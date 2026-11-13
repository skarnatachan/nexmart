import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from account.models import UserProfile
from carts.models import calculate_taxes, get_cart
from store.models import Product
from .forms import CheckoutForm
from . import paypal, tasks
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


def _send_confirmation(request, order):
    context = {
        'full_name': order.full_name(),
        'order_number': order.order_number,
        'payment_method': order.get_payment_method_display(),
        'transaction_id': order.transaction_id,
        'order_date': order.created_at.strftime('%b %d, %Y %H:%M'),
        'status': order.get_status_display(),
        'payment_status': order.get_payment_status_display(),
        'address_lines': [order.address, f'{order.city}, {order.zip_code}', order.country],
        'phone_number': order.phone_number,
        'email': order.email,
        'subtotal': str(order.subtotal), 'tax_total': str(order.tax_total), 'total': str(order.total),
        'address': f'{order.address}, {order.city}, {order.country} {order.zip_code}',
        'lines': [
            {'name': i.product_name, 'color': i.color.title(), 'size': i.size,
             'quantity': i.quantity, 'sub_total': str(i.sub_total())}
            for i in order.items.all()
        ],
        'order_url': request.build_absolute_uri(reverse('order_detail', args=[order.order_number])),
        'logo_url': request.build_absolute_uri('/static/img/favicon/favicon-48x48.png'),
    }
    try:
        tasks.send_order_confirmation_email.delay(context, order.email)
    except Exception:  # a mail/broker outage must not undo a placed order
        logger.exception('Could not queue confirmation email for order %s', order.order_number)


def _active_cart_items(request):
    cart_obj = get_cart(request)
    if not cart_obj:
        return []
    return list(cart_obj.items.filter(is_active=True).select_related('product', 'product__size', 'product__color'))


def _totals(cart_items):
    subtotal = sum((item.sub_total() for item in cart_items), Decimal('0'))
    taxes, tax_total = calculate_taxes(subtotal)
    return subtotal, taxes, tax_total, subtotal + tax_total


def _save_to_profile(user, order, overwrite):
    """Copy the order's shipping data to the user's profile (only empty fields unless overwrite)."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    mapping = {
        'phone_number': order.phone_number, 'shipping_address': order.address,
        'shipping_city': order.city, 'shipping_country': order.country,
        'shipping_zip_code': order.zip_code,
    }
    changed = []
    for field, value in mapping.items():
        if value and (overwrite or not getattr(profile, field)):
            setattr(profile, field, value)
            changed.append(field)
    if changed:
        profile.save(update_fields=changed)


def _initial(user):
    initial = {'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email}
    profile = getattr(user, 'profile', None)
    if profile:
        initial.update(
            phone_number=profile.phone_number, address=profile.shipping_address,
            city=profile.shipping_city, country=profile.shipping_country, zip_code=profile.shipping_zip_code,
        )
    return initial


def _pending_order(request):
    """The unpaid order created by an earlier 'Place order' click in this session, if any."""
    order_id = request.session.get('pending_order_id')
    if not order_id:
        return None
    return Order.objects.filter(pk=order_id, user=request.user, status='awaiting_payment').first()


def _check_stock(cart_items):
    for item in cart_items:
        product = item.product
        if not product.is_available:
            raise ValueError(f'"{product.product_name}" is no longer available.')
        if product.stock < item.quantity:
            raise ValueError(f'Sorry, only {product.stock} of "{product.product_name}" left in stock.')


@login_required
def checkout(request):
    cart_items = _active_cart_items(request)
    if not cart_items:
        messages.info(request, 'Your cart is empty.')
        return redirect('cart')

    subtotal, taxes, tax_total, total = _totals(cart_items)
    pending = _pending_order(request)
    form = CheckoutForm(request.POST or None, instance=pending, initial=_initial(request.user) if not pending else None)

    if request.method == 'POST' and form.is_valid():
        try:
            _check_stock(cart_items)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('cart')

        # Place order only records the order; stock, cart and email are handled when payment is made.
        with transaction.atomic():
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal, order.tax_total, order.total = subtotal, tax_total, total
            order.save()
            order.items.all().delete()
            for item in cart_items:
                product = item.product
                OrderItem.objects.create(
                    order=order, product=product, product_name=product.product_name,
                    size=str(product.size), color=str(product.color),
                    price=product.price, quantity=item.quantity,
                )
            _save_to_profile(request.user, order, overwrite=form.cleaned_data['save_to_profile'])
        request.session['pending_order_id'] = order.pk
        return redirect('payment', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'form': form, 'cart_items': cart_items,
        'subtotal': subtotal, 'taxes': taxes, 'total': total,
    })


def _confirm_order(request, order, *, paid=False, transaction_id='', strict_stock=True):
    """Move an awaiting-payment order to 'new': take stock, clear the cart, send the email.
    Raises ValueError (nothing changed) when strict_stock and an item is unavailable."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != 'awaiting_payment':
            return order
        items = list(order.items.all())
        products = {
            p.id: p for p in Product.objects.select_for_update().filter(
                id__in=[i.product_id for i in items if i.product_id])
        }
        if strict_stock:
            for item in items:
                product = products.get(item.product_id)
                if product is None or not product.is_available:
                    raise ValueError(f'"{item.product_name}" is no longer available.')
                if product.stock < item.quantity:
                    raise ValueError(f'Sorry, only {product.stock} of "{product.product_name}" left in stock.')
        for item in items:
            product = products.get(item.product_id)
            if product:
                if product.stock < item.quantity:
                    logger.warning('Order %s oversold product %s', order.order_number, product.pk)
                product.stock = max(product.stock - item.quantity, 0)
                product.save(update_fields=['stock'])
        order.status = 'new'
        fields = ['status', 'updated_at']
        if paid:
            order.payment_status = 'paid'
            order.transaction_id = transaction_id
            fields += ['payment_status', 'transaction_id']
        order.save(update_fields=fields)
        cart_obj = get_cart(request)
        if cart_obj:
            cart_obj.items.filter(product_id__in=products.keys()).delete()
    request.session.pop('pending_order_id', None)
    _send_confirmation(request, order)
    return order


@login_required
def payment(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status != 'awaiting_payment':
        return redirect('order_detail', order_number=order.order_number)
    uses_paypal = order.payment_method in ('paypal', 'credit_card')

    # Bank transfer has no online step: the button just confirms the order.
    if request.method == 'POST' and not uses_paypal:
        try:
            _confirm_order(request, order)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('cart')
        messages.success(request, f'Order {order.order_number} placed successfully.')
        return redirect('order_complete', order_number=order.order_number)

    return render(request, 'orders/payment.html', {
        'order': order, 'uses_paypal': uses_paypal and paypal.is_configured(),
        'paypal_misconfigured': uses_paypal and not paypal.is_configured(),
        'paypal_client_id': settings.PAYPAL_CLIENT_ID, 'paypal_currency': settings.PAYPAL_CURRENCY,
    })


def _awaiting_order_or_404(request, order_number):
    return get_object_or_404(Order, order_number=order_number, user=request.user, status='awaiting_payment')


@login_required
@require_POST
def paypal_create(request, order_number):
    order = _awaiting_order_or_404(request, order_number)
    if order.payment_method not in ('paypal', 'credit_card'):
        return JsonResponse({'error': 'This order is not paid with PayPal.'}, status=400)
    try:
        for item in order.items.select_related('product'):
            if item.product is None or not item.product.is_available or item.product.stock < item.quantity:
                raise ValueError(f'"{item.product_name}" is not available in the requested quantity.')
        paypal_order_id = paypal.create_order(order)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=409)
    except paypal.PayPalError:
        logger.exception('PayPal create failed for order %s', order.order_number)
        return JsonResponse({'error': 'Could not start the PayPal payment. Please try again.'}, status=502)
    order.paypal_order_id = paypal_order_id
    order.save(update_fields=['paypal_order_id', 'updated_at'])
    return JsonResponse({'id': paypal_order_id})


@login_required
@require_POST
def paypal_capture(request, order_number):
    order = _awaiting_order_or_404(request, order_number)
    try:
        body = json.loads(request.body or '{}')
    except ValueError:
        body = {}
    paypal_order_id = body.get('orderID', '')
    if not paypal_order_id or paypal_order_id != order.paypal_order_id:
        return JsonResponse({'error': 'Unknown PayPal order.'}, status=400)
    try:
        capture = paypal.capture_order(paypal_order_id)
    except paypal.PayPalError:
        logger.exception('PayPal capture failed for order %s', order.order_number)
        return JsonResponse({'error': 'Your PayPal payment could not be completed. You were not charged.'}, status=502)

    amount = capture.get('amount', {})
    if (capture.get('status') != 'COMPLETED' or amount.get('currency_code') != settings.PAYPAL_CURRENCY
            or Decimal(amount.get('value', '0')) != order.total):
        logger.error('PayPal capture mismatch for order %s: %s', order.order_number, capture)
        return JsonResponse({'error': 'The payment was not completed. Please try again.'}, status=402)

    # Money is taken: confirm the order even if stock ran out in the meantime.
    _confirm_order(request, order, paid=True, transaction_id=capture.get('id', ''), strict_stock=False)
    messages.success(request, f'Payment received. Order {order.order_number} placed successfully.')
    return JsonResponse({'redirect': reverse('order_complete', args=[order.order_number])})


@login_required
def order_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_complete.html', {'order': order})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def order_list(request):
    return render(request, 'orders/order_list.html', {'orders': Order.objects.filter(user=request.user)})


@login_required
@require_POST
def order_cancel(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.cancel():
        messages.success(request, f'Order {order.order_number} has been cancelled.')
    else:
        messages.error(request, 'This order can no longer be cancelled.')
    return redirect('order_detail', order_number=order.order_number)
