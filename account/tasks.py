from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _send_html_email(subject, html_template, text_template, context, to_email):
    html_body = render_to_string(html_template, context)
    text_body = render_to_string(text_template, context) if text_template else strip_tags(html_body)
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_email])
    message.attach_alternative(html_body, 'text/html')
    message.send()


@shared_task
def send_activation_email(context, to_email):
    _send_html_email(
        'Activate your Nexmart account',
        'account/email/activation_email.html',
        'account/email/activation_email.txt',
        context,
        to_email,
    )


@shared_task
def send_welcome_email(context, to_email):
    _send_html_email(
        'Welcome to Nexmart - account confirmation',
        'account/email/welcome_email.html',
        'account/email/welcome_email.txt',
        context,
        to_email,
    )


@shared_task
def send_password_reset_email(subject, context, to_email):
    _send_html_email(
        subject,
        'account/email/password_reset_email.html',
        'account/email/password_reset_email.txt',
        context,
        to_email,
    )


@shared_task
def send_password_changed_email(context, to_email):
    _send_html_email(
        'Your Nexmart password was changed',
        'account/email/password_changed_email.html',
        'account/email/password_changed_email.txt',
        context,
        to_email,
    )
