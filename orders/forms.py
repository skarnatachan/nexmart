from django import forms

from account.forms import StyledFormMixin
from .models import Order


class CheckoutForm(StyledFormMixin, forms.ModelForm):
    save_to_profile = forms.BooleanField(
        required=False, initial=True, label='Save this shipping address to my profile',
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-default-medium text-brand focus:ring-brand'}),
    )

    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'address', 'city', 'country', 'zip_code',
            'payment_method', 'order_note',
        ]
        widgets = {
            'order_note': forms.Textarea(attrs={'rows': 3}),
            'payment_method': forms.RadioSelect,
        }
        labels = {'zip_code': 'ZIP / postal code', 'order_note': 'Order note (optional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # StyledFormMixin gives every widget `.input`; a checkbox must not use it.
        self.fields['save_to_profile'].widget.attrs['class'] = (
            'h-4 w-4 rounded border-default-medium text-brand focus:ring-brand')
