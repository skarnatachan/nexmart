from decimal import Decimal
from .models import calculate_taxes, get_cart


def cart_summary(request):
    cart_items = []
    cart_obj = get_cart(request)
    if cart_obj:
        cart_items = cart_obj.items.filter(is_active=True).select_related('product')
    subtotal = sum((item.sub_total() for item in cart_items), Decimal('0'))
    taxes, tax_total = calculate_taxes(subtotal)
    return {
        'nav_cart_items': cart_items,
        'nav_cart_count': sum(item.quantity for item in cart_items),
        'nav_subtotal': subtotal,
        'nav_taxes': taxes,
        'nav_cart_total': subtotal + tax_total,
    }
