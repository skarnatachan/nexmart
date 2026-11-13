from django.test import TestCase
from django.urls import reverse

from account.models import User
from carts.models import Cart
from category.models import Category
from store.models import Color, Product, Size


class CartLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', 'A', 'B', 'u1@example.com', 'Testpass123!')
        self.user.is_active = True
        self.user.save()
        cat = Category.objects.create(category_name='Cat', slug='cat')
        self.product = Product.objects.create(
            product_name='Shirt', price=10, stock=5, category=cat,
            size=Size.objects.get_or_create(code='TST', defaults={'label': 'Test'})[0], color=Color.objects.get_or_create(code='tst', defaults={'label': 'Tst'})[0],
        )

    def _login(self):
        return self.client.post(reverse('login'), {'username': 'u1@example.com', 'password': 'Testpass123!'})

    def _cart_qty(self):
        return [i.quantity for i in self.client.get(reverse('cart')).context['cart_items']]

    def test_guest_cart_survives_login_and_logout(self):
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self.assertEqual(self._login().status_code, 302)
        self.assertEqual(self._cart_qty(), [2])
        self.client.post(reverse('logout'))
        self.assertEqual(self._cart_qty(), [])
        self._login()
        self.assertEqual(self._cart_qty(), [2])

    def test_legacy_session_keyed_cart_survives_login(self):
        self.client.get(reverse('home'))
        session = self.client.session
        session.save()
        legacy = Cart.objects.create(cart_id=session.session_key)
        legacy.items.create(product=self.product, quantity=3)
        self._login()
        self.assertEqual(self._cart_qty(), [3])


class CheckoutPaymentTests(CartLoginTests):
    def test_payment_options_render_and_order_saves(self):
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        html = self.client.get(reverse('checkout')).content.decode()
        for label in ('PayPal', 'Credit Card', 'Bank Transfer'):
            self.assertIn(label, html)
        self.assertNotIn('Cash on delivery', html)
        data = dict(first_name='A', last_name='B', email='a@b.com', phone_number='1', address='x',
                    city='c', country='id', zip_code='1', payment_method='credit_card', order_note='')
        r = self.client.post(reverse('checkout'), data)
        self.assertEqual(r.status_code, 302)
        from orders.models import Order
        self.assertEqual(Order.objects.get().payment_method, 'credit_card')


class PlaceOrderTests(CartLoginTests):
    DATA = dict(first_name='A', last_name='B', email='a@b.com', phone_number='1', address='x',
                city='c', country='id', zip_code='1', payment_method='bank_transfer', order_note='')

    def test_place_order_then_pay_and_cancel(self):
        from unittest import mock
        from orders.models import Order
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        with mock.patch('orders.views.tasks.send_order_confirmation_email.delay') as mail:
            r = self.client.post(reverse('checkout'), self.DATA)
            order = Order.objects.get()
            self.assertRedirects(r, reverse('payment', args=[order.order_number]))
            # Place order: no email, no stock change, cart intact.
            mail.assert_not_called()
            self.product.refresh_from_db()
            self.assertEqual((self.product.stock, order.status), (5, 'awaiting_payment'))
            self.assertEqual(self._cart_qty(), [2])
            page = self.client.get(r.url).content.decode()
            for text in ('Billing address', 'Bank Transfer', 'Shirt', 'Grand total', 'Confirm order', 'Back to cart'):
                self.assertIn(text, page)
            # Going back and placing again reuses the same pending order.
            self.client.post(reverse('checkout'), self.DATA)
            self.assertEqual(Order.objects.count(), 1)
            # Confirm (bank transfer).
            r = self.client.post(reverse('payment', args=[order.order_number]))
            self.assertRedirects(r, reverse('order_complete', args=[order.order_number]))
            mail.assert_called_once()
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((order.status, self.product.stock), ('new', 3))
        self.assertEqual(self._cart_qty(), [])
        self.assertEqual(self.client.get(reverse('order_complete', args=[order.order_number])).status_code, 200)
        # Paying again is not possible; cancelling restores stock.
        self.assertRedirects(self.client.get(reverse('payment', args=[order.order_number])),
                             reverse('order_detail', args=[order.order_number]))
        self.client.post(reverse('order_cancel', args=[order.order_number]))
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((order.status, self.product.stock), ('cancelled', 5))

    def test_cancel_unpaid_order_keeps_stock(self):
        from orders.models import Order
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        self.client.post(reverse('checkout'), self.DATA)
        order = Order.objects.get()
        self.client.post(reverse('order_cancel', args=[order.order_number]))
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((order.status, self.product.stock), ('cancelled', 5))

    def test_mail_failure_does_not_break_order(self):
        from unittest import mock
        from orders.models import Order
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        with mock.patch('orders.views.tasks.send_order_confirmation_email.delay', side_effect=OSError):
            self.client.post(reverse('checkout'), self.DATA)
            order = Order.objects.get()
            r = self.client.post(reverse('payment', args=[order.order_number]))
        self.assertEqual(r.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'new')

    def test_cannot_cancel_other_users_order(self):
        from orders.models import Order
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        self.client.post(reverse('checkout'), self.DATA)
        order = Order.objects.get()
        other = User.objects.create_user('u2', 'C', 'D', 'u2@example.com', 'Testpass123!')
        other.is_active = True; other.save()
        self.client.logout(); self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('order_cancel', args=[order.order_number])).status_code, 404)


class ProfileAddressTests(PlaceOrderTests):
    def _place(self, **extra):
        self.client.post(reverse('add_cart', args=[self.product.id]))
        return self.client.post(reverse('checkout'), {**self.DATA, **extra})

    def test_prefill_and_save_to_profile(self):
        from unittest import mock
        profile = self.user.profile
        profile.shipping_address = 'Old St'; profile.shipping_city = 'Old City'; profile.save()
        self._login()
        self.client.post(reverse('add_cart', args=[self.product.id]))
        html = self.client.get(reverse('checkout')).content.decode()
        self.assertIn('Old St', html)
        with mock.patch('orders.views.tasks.send_order_confirmation_email.delay'):
            self.client.post(reverse('checkout'), {**self.DATA, 'address': 'New Ave', 'save_to_profile': 'on'})
        profile.refresh_from_db()
        self.assertEqual((profile.shipping_address, profile.shipping_city, profile.phone_number), ('New Ave', 'c', '1'))

    def test_unchecked_keeps_existing_but_fills_empty(self):
        from unittest import mock
        profile = self.user.profile
        profile.shipping_address = 'Old St'; profile.save()
        self._login()
        with mock.patch('orders.views.tasks.send_order_confirmation_email.delay'):
            self._place(address='New Ave')
        profile.refresh_from_db()
        self.assertEqual((profile.shipping_address, profile.shipping_city), ('Old St', 'c'))


class PayPalTests(PlaceOrderTests):
    PP = dict(PlaceOrderTests.DATA, payment_method='paypal')

    def _to_payment(self):
        from orders.models import Order
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self.client.post(reverse('add_cart', args=[self.product.id]))
        self._login()
        self.client.post(reverse('checkout'), self.PP)
        return Order.objects.get()

    def test_payment_page_shows_paypal_button_not_make_payment(self):
        from django.test import override_settings
        with override_settings(PAYPAL_CLIENT_ID='cid', PAYPAL_SECRET_KEY='sec'):
            order = self._to_payment()
            html = self.client.get(reverse('payment', args=[order.order_number])).content.decode()
        self.assertIn('paypal-button-container', html)
        self.assertIn('sdk/js?client-id=cid', html)
        self.assertNotIn('Make payment', html)

    def test_create_and_capture_marks_paid(self):
        from unittest import mock
        order = self._to_payment()
        with mock.patch('orders.views.paypal.create_order', return_value='PP-1'), \
                mock.patch('orders.views.tasks.send_order_confirmation_email.delay') as mail:
            r = self.client.post(reverse('paypal_create', args=[order.order_number]))
            self.assertEqual(r.json(), {'id': 'PP-1'})
            capture = {'id': 'CAP-9', 'status': 'COMPLETED', 'amount': {'currency_code': 'USD', 'value': f'{order.total:.2f}'}}
            with mock.patch('orders.views.paypal.capture_order', return_value=capture):
                r = self.client.post(reverse('paypal_capture', args=[order.order_number]),
                                     {'orderID': 'PP-1'}, content_type='application/json')
            mail.assert_called_once()
        self.assertEqual(r.json()['redirect'], reverse('order_complete', args=[order.order_number]))
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual((order.status, order.payment_status, order.transaction_id), ('new', 'paid', 'CAP-9'))
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self._cart_qty(), [])

    def test_capture_rejects_wrong_id_and_wrong_amount(self):
        from unittest import mock
        order = self._to_payment()
        with mock.patch('orders.views.paypal.create_order', return_value='PP-1'):
            self.client.post(reverse('paypal_create', args=[order.order_number]))
        url = reverse('paypal_capture', args=[order.order_number])
        r = self.client.post(url, {'orderID': 'OTHER'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        bad = {'id': 'C', 'status': 'COMPLETED', 'amount': {'currency_code': 'USD', 'value': '0.01'}}
        with mock.patch('orders.views.paypal.capture_order', return_value=bad):
            r = self.client.post(url, {'orderID': 'PP-1'}, content_type='application/json')
        self.assertEqual(r.status_code, 402)
        order.refresh_from_db()
        self.assertEqual((order.status, order.payment_status), ('awaiting_payment', 'pending'))

    def test_cannot_confirm_paypal_order_without_paying(self):
        order = self._to_payment()
        self.client.post(reverse('payment', args=[order.order_number]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'awaiting_payment')
