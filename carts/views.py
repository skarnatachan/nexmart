from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from store.models import Product
from .models import CartItem, calculate_taxes, get_cart


def _get_cart(request):
    return get_cart(request, create=True)


def _redirect_back(request):
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('cart')


@require_POST
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    cart_item, created = CartItem.objects.get_or_create(
        product=product, cart=_get_cart(request),
        defaults={'size': product.size, 'color': product.color},
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return _redirect_back(request)


@require_POST
def remove_cart(request, product_id):
    cart_item = CartItem.objects.filter(product_id=product_id, cart=_get_cart(request)).first()
    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    return _redirect_back(request)


@require_POST
def remove_cart_item(request, product_id):
    CartItem.objects.filter(product_id=product_id, cart=_get_cart(request)).delete()
    return _redirect_back(request)


def cart(request):
    cart_obj = get_cart(request)
    cart_items = CartItem.objects.none()
    if cart_obj:
        cart_items = cart_obj.items.filter(is_active=True).select_related('product')
    subtotal = sum((item.sub_total() for item in cart_items), Decimal('0'))
    taxes, tax_total = calculate_taxes(subtotal)

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'taxes': taxes,
        'total': subtotal + tax_total,
    }
    return render(request, 'carts/cart.html', context)
