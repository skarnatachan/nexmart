from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from store.models import Product, Tax


def calculate_taxes(subtotal):
    taxes = []
    for tax in Tax.objects.filter(is_active=True):
        amount = (subtotal * tax.tax_value / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        taxes.append({'tax': tax, 'amount': amount})
    tax_total = sum((row['amount'] for row in taxes), Decimal('0'))
    return taxes, tax_total


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, unique=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=2, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return self.product.product_name

    class Meta:
        unique_together = ('cart', 'product')

