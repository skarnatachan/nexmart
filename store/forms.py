from django import forms


class ProductSearchForm(forms.Form):
    q = forms.CharField(max_length=200, required=False, strip=True)
