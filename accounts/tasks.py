from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from core.logger import logger


@shared_task
def send_password_reset_email(email, reset_url):
    """Email a one-time password reset link.

    Runs asynchronously via Celery.
    Raises on SMTP failure so the task can retry.
    """
    try:
        subject = "Reset your Deskline password"
        message = (
            f"Hi,\n\n"
            f"You requested a password reset for your Deskline account.\n\n"
            f"Click the link below to set a new password:\n{reset_url}\n\n"
            f"This link expires in 1 hour. If you didn't request this, you can safely ignore this email.\n\n"
            f"— The Deskline Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"[RESET EMAIL] Sent to {email}")
    except Exception as e:
        logger.error(f"[RESET EMAIL] Failed for {email}: {e}")
        raise
