"""Minimal PayPal Orders v2 client (standard library only)."""
import base64
import json
import urllib.error
import urllib.request

from django.conf import settings


class PayPalError(Exception):
    pass


def _request(method, path, payload=None, token=None, basic=None, form=None, request_id=None):
    headers = {'Accept': 'application/json'}
    data = None
    if basic:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'{basic[0]}:{basic[1]}'.encode()).decode()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if form is not None:
        data = '&'.join(f'{k}={v}' for k, v in form.items()).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    elif payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    if request_id:
        headers['PayPal-Request-Id'] = request_id
    req = urllib.request.Request(settings.PAYPAL_API_BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')
        raise PayPalError(f'PayPal API error {exc.code}: {detail}') from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PayPalError(f'Could not reach PayPal: {exc}') from exc


def is_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_SECRET_KEY)


def get_access_token():
    result = _request('POST', '/v1/oauth2/token', basic=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_KEY),
                      form={'grant_type': 'client_credentials'})
    return result['access_token']


def create_order(order):
    """Create a PayPal order for our Order and return the PayPal order id."""
    currency = settings.PAYPAL_CURRENCY
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': order.order_number,
            'custom_id': order.order_number,
            'description': f'Nexmart order {order.order_number}',
            'amount': {
                'currency_code': currency,
                'value': f'{order.total:.2f}',
                'breakdown': {
                    'item_total': {'currency_code': currency, 'value': f'{order.subtotal:.2f}'},
                    'tax_total': {'currency_code': currency, 'value': f'{order.tax_total:.2f}'},
                },
            },
        }],
    }
    result = _request('POST', '/v2/checkout/orders', payload, token=get_access_token(),
                      request_id=f'create-{order.order_number}-{order.total:.2f}')
    return result['id']


def capture_order(paypal_order_id):
    """Capture an approved PayPal order. Returns the capture dict (id, status, amount)."""
    token = get_access_token()
    try:
        result = _request('POST', f'/v2/checkout/orders/{paypal_order_id}/capture', {}, token=token,
                          request_id=f'capture-{paypal_order_id}')
    except PayPalError as exc:
        if 'ORDER_ALREADY_CAPTURED' not in str(exc):
            raise
        result = _request('GET', f'/v2/checkout/orders/{paypal_order_id}', token=token)
    try:
        return result['purchase_units'][0]['payments']['captures'][0]
    except (KeyError, IndexError) as exc:
        raise PayPalError('PayPal returned no capture for this order.') from exc
