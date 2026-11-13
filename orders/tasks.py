from celery import shared_task

from account.tasks import _send_html_email


@shared_task
def send_order_confirmation_email(context, to_email):
    _send_html_email(
        f"Your Nexmart order {context['order_number']}",
        'orders/email/order_confirmation.html',
        'orders/email/order_confirmation.txt',
        context,
        to_email,
    )
