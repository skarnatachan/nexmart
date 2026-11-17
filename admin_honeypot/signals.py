from django.dispatch import Signal

# Sent with `instance` (LoginAttempt) and `request` whenever the fake login form is submitted.
honeypot = Signal()
