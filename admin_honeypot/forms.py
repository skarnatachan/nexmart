from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm


class HoneypotLoginForm(AdminAuthenticationForm):
    def clean(self):
        """Always fail with the default error, whatever was entered."""
        raise forms.ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
            params={'username': self.username_field.verbose_name},
        )
