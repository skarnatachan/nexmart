from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from account.models import User
from admin_honeypot.models import LoginAttempt


class AdminHoneypotTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'B', 'S', 'boss@example.com', 'Testpass123!')
        self.real = f'/{settings.ADMIN_URL}/'

    def test_fake_admin_redirects_to_fake_login(self):
        r = self.client.get('/admin/store/product/')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith('/admin/login/?next='))

    def test_fake_login_logs_attempt_and_never_authenticates(self):
        # Even the REAL superuser credentials must fail on the honeypot.
        r = self.client.post('/admin/login/', {'username': 'boss@example.com', 'password': 'Testpass123!'},
                             HTTP_USER_AGENT='sqlmap', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        attempt = LoginAttempt.objects.get()
        self.assertEqual((attempt.username, attempt.ip_address, attempt.user_agent), ('boss@example.com', '203.0.113.9', 'sqlmap'))

    def test_real_admin_moved_and_works(self):
        self.assertEqual(self.client.get(self.real).status_code, 302)  # login redirect, not 404
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.real).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:admin_honeypot_loginattempt_changelist')).status_code, 200)

    def test_honeypot_page_does_not_leak_real_admin_url(self):
        html = self.client.get('/admin/login/').content.decode()
        self.assertIn('Log in', html)
        self.assertNotIn(self.real, html)

    def test_attempt_list_escapes_attacker_input(self):
        self.client.post('/admin/login/?x=<script>', {'username': '<script>alert(1)</script>', 'password': 'x'})
        self.client.force_login(self.admin)
        html = self.client.get(reverse('admin:admin_honeypot_loginattempt_changelist')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
