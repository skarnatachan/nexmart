import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django_session_timeout.middleware import SESSION_TIMEOUT_KEY, SessionTimeoutMiddleware


class AuthenticatedSessionTimeoutMiddleware(SessionTimeoutMiddleware):
    """django-session-timeout, but only for logged-in users.

    The stock middleware also expires anonymous sessions, which would redirect guests browsing the
    shop to the login page and throw away their guest cart. Must come after Authentication and Message middleware.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        init_time = request.session.get(SESSION_TIMEOUT_KEY)
        expire_seconds = getattr(settings, 'SESSION_EXPIRE_SECONDS', settings.SESSION_COOKIE_AGE)
        expired = init_time is not None and time.time() - init_time > expire_seconds

        response = super().process_request(request)
        if expired:
            # The session was flushed by the parent; tell the user why they are at the login page.
            messages.info(request, 'You were logged out after %d minutes of inactivity. Please log in again.'
                          % (expire_seconds // 60))
            if request.content_type == 'application/json':  # fetch() calls, e.g. the PayPal buttons
                return JsonResponse({'error': 'Your session expired. Please log in again.',
                                     'login_url': settings.LOGIN_URL}, status=401)
            if response is None:
                return redirect_to_login(next=request.path)
        return response
