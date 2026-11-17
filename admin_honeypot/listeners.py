from django.conf import settings
from django.core.mail import mail_admins
from django.template.loader import render_to_string
from django.urls import reverse

from admin_honeypot.signals import honeypot


def notify_admins(instance, request, **kwargs):
    path = reverse('admin:admin_honeypot_loginattempt_change', args=(instance.pk,))
    context = {
        'request': request,
        'instance': instance,
        'admin_detail_url': request.build_absolute_uri(path),
    }
    subject = render_to_string('admin_honeypot/email_subject.txt', context).strip()
    message = render_to_string('admin_honeypot/email_message.txt', context).strip()
    # Never let a mail outage turn a bot request into a server error.
    mail_admins(subject=subject, message=message, fail_silently=True)


# Off by default: every bot hit would otherwise send an e-mail. Enable in settings if wanted.
if getattr(settings, 'ADMIN_HONEYPOT_EMAIL_ADMINS', False):
    honeypot.connect(notify_admins)
