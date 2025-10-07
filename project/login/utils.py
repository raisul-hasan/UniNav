import random
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    subject = "Your Login OTP Code"
    message = f"Your OTP code is {otp}. Do not share it with anyone."
    from_email = settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise Exception(f"Failed to send OTP email: {str(e)}")