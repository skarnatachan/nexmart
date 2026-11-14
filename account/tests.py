import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from account.models import User

TEMP_MEDIA = tempfile.mkdtemp()


def _image(name='me.png', size=(20, 20)):
    buf = io.BytesIO()
    Image.new('RGB', size, 'red').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfilePhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('p1', 'A', 'B', 'p1@example.com', 'Testpass123!')
        self.user.is_active = True
        self.user.save()
        self.client.force_login(self.user)

    def _post(self, **extra):
        data = {'first_name': 'A', 'last_name': 'B', 'username': 'p1', 'email': 'p1@example.com', **extra}
        return self.client.post(reverse('profile'), data)

    def test_upload_replace_and_remove_photo(self):
        self.assertEqual(self._post(photo=_image('one.png')).status_code, 302)
        profile = self.user.profile
        profile.refresh_from_db()
        first = profile.photo.name
        self.assertTrue(first.startswith('images/users/'))
        self.assertIn(profile.photo.url, self.client.get(reverse('profile')).content.decode())
        self.assertIn(profile.photo.url, self.client.get(reverse('home')).content.decode())  # navbar avatar

        self._post(photo=_image('two.png'))
        profile.refresh_from_db()
        self.assertNotEqual(profile.photo.name, first)
        self.assertFalse(profile.photo.storage.exists(first))  # old file cleaned up

        self._post(remove_photo='on')
        profile.refresh_from_db()
        self.assertFalse(profile.photo)

    def test_rejects_non_image_and_oversize_and_both(self):
        bad = SimpleUploadedFile('x.txt', b'not an image', content_type='text/plain')
        self.assertEqual(self._post(photo=bad).status_code, 200)
        big = SimpleUploadedFile('big.png', _image().read() + b'0' * (2 * 1024 * 1024), content_type='image/png')
        self.assertEqual(self._post(photo=big).status_code, 200)
        self.assertFalse(self.user.profile.photo)
        self._post(photo=_image())
        r = self._post(photo=_image(), remove_photo='on')
        self.assertEqual(r.status_code, 200)

    def test_profile_saves_without_photo_change(self):
        self._post(photo=_image())
        self.user.profile.refresh_from_db()
        name = self.user.profile.photo.name
        self.assertTrue(name)
        self._post()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.photo.name, name)
