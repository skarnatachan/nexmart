from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse_lazy

from . import tasks
from .forms import (
    CustomPasswordResetForm,
    EmailAuthenticationForm,
    RegistrationForm,
    StyledPasswordChangeForm,
    StyledSetPasswordForm,
    UserProfileForm,
    UserUpdateForm,
)
from .models import UserProfile


def _logo_url(request):
    return request.build_absolute_uri(static('img/logo/nexmart-logo.png'))


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            tasks.send_welcome_email.delay(
                {
                    'full_name': user.get_full_name(),
                    'email': user.email,
                    'logo_url': _logo_url(request),
                    'site_url': request.build_absolute_uri('/'),
                },
                user.email,
            )
            auth_login(request, user)
            messages.success(request, 'Welcome to Nexmart! Your account has been created.')
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'account/register.html', {'form': form})


class EmailLoginView(LoginView):
    template_name = 'account/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


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
