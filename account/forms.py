from datetime import date

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, UserProfile


class StyledFormMixin:
    """Gives every field's widget the project's shared `.input` CSS class."""
    default_css_class = 'input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            classes = f"{existing} {self.default_css_class}".strip()
            if isinstance(field.widget, forms.PasswordInput):
                classes = f"{classes} pr-10".strip()
            field.widget.attrs['class'] = classes


class RegistrationForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(label='Password', min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'autofocus': True}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = False
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                existing = User.objects.filter(email__iexact=email).first()
                if existing and not existing.is_active and existing.check_password(password):
                    raise ValidationError(
                        mark_safe(
                            'Your account is not active yet. Please check your email for the '
                            'activation link, or <a href="%s" class="link">request a new one</a>.'
                            % reverse('resend_activation')
                        ),
                        code='inactive',
                    )
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class ResendActivationForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))


class CustomPasswordResetForm(StyledFormMixin, PasswordResetForm):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        from . import tasks

        user = context['user']
        safe_context = {
            'full_name': user.get_full_name(),
            'email': context['email'],
            'domain': context['domain'],
            'site_name': context['site_name'],
            'uid': context['uid'],
            'token': context['token'],
            'protocol': context['protocol'],
            'logo_url': f"{context['protocol']}://{context['domain']}{static('img/logo/nexmart-logo.png')}",
        }
        subject = ''.join(render_to_string(subject_template_name, safe_context).splitlines())
        tasks.send_password_reset_email.delay(subject, safe_context, to_email)


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    pass


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']


MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2 MB


class UserProfileForm(StyledFormMixin, forms.ModelForm):
    remove_photo = forms.BooleanField(required=False, label='Remove photo')

    class Meta:
        model = UserProfile
        fields = [
            'photo', 'date_of_birth', 'gender', 'phone_number',
            'shipping_address', 'shipping_city', 'shipping_country', 'shipping_zip_code',
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo'].widget.attrs['class'] = 'input file:me-3 file:cursor-pointer'
        self.fields['remove_photo'].widget.attrs['class'] = 'h-4 w-4 rounded border-default-medium text-brand focus:ring-brand'
        self.fields['date_of_birth'].widget.attrs['max'] = date.today().isoformat()
        self._old_photo_name = self.instance.photo.name if self.instance and self.instance.photo else ''

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size') and photo.size > MAX_PHOTO_SIZE:
            raise ValidationError('Photo must be 2 MB or smaller.')
        return photo

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('remove_photo') and self.files.get('photo'):
            self.add_error('remove_photo', 'Choose either a new photo or "Remove photo", not both.')
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        old_name = self._old_photo_name
        if self.cleaned_data.get('remove_photo'):
            profile.photo = ''
        if commit:
            profile.save()
            # Don't leave replaced/removed photos behind on disk.
            if old_name and old_name != (profile.photo.name if profile.photo else ''):
                profile.photo.storage.delete(old_name)
        return profile

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > date.today():
            raise ValidationError('Date of birth cannot be in the future.')
        return date_of_birth
