from decimal import Decimal

from django import forms

from .models import Review


class ProductSearchForm(forms.Form):
    q = forms.CharField(max_length=200, required=False, strip=True)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput,
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'input', 'placeholder': 'Share your experience with this product'}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None:
            raise forms.ValidationError('Please choose a star rating.')
        if rating < Decimal('0.5') or rating > 5 or (rating * 2) % 1 != 0:
            raise forms.ValidationError('Rating must be between 0.5 and 5 in half-star steps.')
        return rating
