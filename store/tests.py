from django.test import TestCase

from decimal import Decimal

from django.urls import reverse

from account.models import User
from category.models import Category
from orders.models import Order, OrderItem
from store.models import Color, Product, Review, Size


class ReviewTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(category_name='Cat', slug='cat')
        self.size = Size.objects.get_or_create(code='TST', defaults={'label': 'Test'})[0]
        self.red = Color.objects.get_or_create(code='tstr', defaults={'label': 'R'})[0]
        self.blue = Color.objects.get_or_create(code='tstb', defaults={'label': 'B'})[0]
        self.red_p = Product.objects.create(product_name='Shirt', price=10, stock=5, category=self.cat, size=self.size, color=self.red)
        self.blue_p = Product.objects.create(product_name='Shirt', price=10, stock=5, category=self.cat, size=self.size, color=self.blue)
        self.buyer = self._user('buyer')
        self.other = self._user('other')
        order = Order.objects.create(user=self.buyer, first_name='A', last_name='B', email='a@b.c', phone_number='1',
                                     address='x', city='c', country='i', zip_code='1', subtotal=10, total=10, status='new')
        OrderItem.objects.create(order=order, product=self.red_p, product_name='Shirt', price=10, quantity=1)
        self.url = reverse('review_submit', args=['cat', self.red_p.slug])
        self.detail = reverse('products_detail', args=['cat', self.red_p.slug])

    def _user(self, name):
        u = User.objects.create_user(name, 'F', 'L', f'{name}@example.com', 'Testpass123!')
        u.is_active = True
        u.save()
        return u

    def test_buyer_can_review_with_half_star_on_any_variant_page(self):
        self.client.force_login(self.buyer)
        blue_url = reverse('products_detail', args=['cat', self.blue_p.slug])
        self.assertContains(self.client.get(blue_url), 'id="star-rating"')
        r = self.client.post(reverse('review_submit', args=['cat', self.blue_p.slug]), {'rating': '3.5', 'comment': 'Nice'})
        self.assertEqual(r.status_code, 302)
        review = Review.objects.get()
        self.assertEqual((review.rating, review.product, review.user), (Decimal('3.5'), self.red_p, self.buyer))
        page = self.client.get(self.detail).content.decode()
        self.assertIn('3.5 out of 5', page)
        self.assertIn('Verified purchase', page)

    def test_second_submit_updates_and_delete_works(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url, {'rating': '4', 'comment': 'a'})
        self.client.post(self.url, {'rating': '5', 'comment': 'b'})
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, Decimal('5.0'))
        self.client.post(reverse('review_delete', args=['cat', self.red_p.slug]))
        self.assertEqual(Review.objects.count(), 0)

    def test_non_buyer_and_anonymous_cannot_review(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.detail), 'id="star-rating"')
        self.client.post(self.url, {'rating': '4', 'comment': 'x'})
        self.assertEqual(Review.objects.count(), 0)
        self.client.logout()
        r = self.client.post(self.url, {'rating': '4', 'comment': 'x'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)
        self.assertEqual(Review.objects.count(), 0)

    def test_unconfirmed_order_does_not_count_and_bad_ratings_rejected(self):
        Order.objects.update(status='awaiting_payment')
        self.client.force_login(self.buyer)
        self.client.post(self.url, {'rating': '4', 'comment': 'x'})
        self.assertEqual(Review.objects.count(), 0)
        Order.objects.update(status='new')
        for bad in ('0', '5.5', '3.3', ''):
            self.client.post(self.url, {'rating': bad, 'comment': 'x'})
        self.assertEqual(Review.objects.count(), 0)


class ListingRatingTests(ReviewTests):
    def test_home_and_store_show_average_stars(self):
        Review.objects.create(product=self.red_p, user=self.buyer, name='A', rating=Decimal('4.5'), comment='x')
        Review.objects.create(product=self.blue_p, user=self.other, name='B', rating=Decimal('3.5'), comment='y')
        for name in ('home', 'store'):
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn('4.0', html)
            self.assertIn('(2)', html)
