from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import models
from store.models import Product, Tax


def calculate_taxes(subtotal):
    taxes = []
    for tax in Tax.objects.filter(is_active=True):
        amount = (subtotal * tax.tax_value / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        taxes.append({'tax': tax, 'amount': amount})
    tax_total = sum((row['amount'] for row in taxes), Decimal('0'))
    return taxes, tax_total


def get_cart_id(request, create=False):
    """Cart key stored in the session so it survives login (which rotates the session key)."""
    cart_id = request.session.get('cart_id')
    if cart_id:
        return cart_id
    if not request.session.session_key:
        if not create:
            return None
        request.session.create()
    if not create:
        return request.session.session_key
    request.session['cart_id'] = request.session.session_key
    return request.session['cart_id']


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='cart',
    )
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return self.product.product_name

    class Meta:
        unique_together = ('cart', 'product')



def get_cart(request, create=False):
    """Return the current cart: the user's own cart when logged in, else the session cart."""
    user = request.user
    if user.is_authenticated:
        cart = Cart.objects.filter(user=user).first()
        if cart is None and create:
            cart = Cart.objects.create(user=user, cart_id=f'user-{user.pk}')
        return cart
    cart_id = get_cart_id(request, create=create)
    if not cart_id:
        return None
    if create:
        return Cart.objects.get_or_create(cart_id=cart_id)[0]
    return Cart.objects.filter(cart_id=cart_id).first()


def merge_session_cart(request, user, guest_cart_id=None):
    """Move items from the anonymous session cart into the user's persistent cart."""
    cart_id = request.session.pop('cart_id', None) or guest_cart_id
    if not cart_id:
        return
    guest_cart = Cart.objects.filter(cart_id=cart_id, user__isnull=True).first()
    if not guest_cart:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user, defaults={'cart_id': f'user-{user.pk}'})
    for item in guest_cart.items.all():
        existing = user_cart.items.filter(product_id=item.product_id).first()
        if existing:
            existing.quantity += item.quantity
            existing.save()
            item.delete()
        else:
            item.cart = user_cart
            item.save()
    guest_cart.delete()
