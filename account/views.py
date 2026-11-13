from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from . import tasks
from carts.models import merge_session_cart
from .forms import (
    CustomPasswordResetForm,
    EmailAuthenticationForm,
    RegistrationForm,
    ResendActivationForm,
    StyledPasswordChangeForm,
    StyledSetPasswordForm,
    UserProfileForm,
    UserUpdateForm,
)
from .models import User, UserProfile


def _logo_url(request):
    return request.build_absolute_uri(static('img/logo/nexmart-logo.png'))


def _send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_path = reverse('activate', kwargs={'uidb64': uid, 'token': token})
    tasks.send_activation_email.delay(
        {
            'full_name': user.get_full_name(),
            'activation_url': request.build_absolute_uri(activation_path),
            'logo_url': _logo_url(request),
        },
        user.email,
    )


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            _send_activation_email(request, user)
            return redirect('activation_sent')
    else:
        form = RegistrationForm()
    return render(request, 'account/register.html', {'form': form})


class CustomLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Must come after super().post(), since logout() flushes the session
        # that messages are stored in.
        messages.success(request, 'You have been logged out from Nexmart system.', extra_tags='logout-modal')
        return response


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    activated = False
    if user is not None and default_token_generator.check_token(user, token):
        activated = True
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            tasks.send_welcome_email.delay(
                {
                    'full_name': user.get_full_name(),
                    'email': user.email,
                    'logo_url': _logo_url(request),
                    'site_url': request.build_absolute_uri('/'),
                },
                user.email,
            )

    return render(request, 'account/activation_complete.html', {'activated': activated})


def resend_activation(request):
    if request.method == 'POST':
        form = ResendActivationForm(request.POST)
        if form.is_valid():
            user = User.objects.filter(email__iexact=form.cleaned_data['email']).first()
            if user and not user.is_active:
                _send_activation_email(request, user)
            return redirect('activation_sent')
    else:
        form = ResendActivationForm()
    return render(request, 'account/resend_activation_form.html', {'form': form})


def activation_sent(request):
    return render(request, 'account/activation_sent.html')


class EmailLoginView(LoginView):
    template_name = 'account/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Login rotates the session key, so remember the guest cart's key first.
        guest_cart_id = self.request.session.get('cart_id') or self.request.session.session_key
        response = super().form_valid(form)
        merge_session_cart(self.request, self.request.user, guest_cart_id)
        messages.success(self.request, f'Welcome back, {self.request.user.get_full_name()}! You have been logged in successfully.')
        return response


class CustomPasswordResetView(PasswordResetView):
    template_name = 'account/password_reset_form.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'account/email/password_reset_email.txt'
    subject_template_name = 'account/email/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'account/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'account/password_reset_confirm.html'
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        tasks.send_password_changed_email.delay(
            {
                'full_name': user.get_full_name(),
                'logo_url': _logo_url(self.request),
            },
            user.email,
        )
        return response


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'account/password_reset_complete.html'


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'account/password_change_form.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        tasks.send_password_changed_email.delay(
            {
                'full_name': self.request.user.get_full_name(),
                'logo_url': _logo_url(self.request),
            },
            self.request.user.email,
        )
        messages.success(self.request, 'Your password has been changed.')
        return response


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'account/password_change_done.html'


@login_required
def profile(request):
    user_profile, _created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=user_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)

    return render(request, 'account/profile.html', {'user_form': user_form, 'profile_form': profile_form})
