"""Email sending helpers (transactional emails).

All senders go through Django's mail backend (`EMAIL_BACKEND`). Locally the
default is the file backend, so no SMTP is required in dev/CI.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerificationToken

VERIFICATION_TOKEN_TTL = timedelta(hours=24)


def create_verification_token(user) -> EmailVerificationToken:
    """Create (or replace) a single-use email verification token for a user."""
    token, _ = EmailVerificationToken.objects.update_or_create(
        user=user,
        defaults={
            "token": uuid.uuid4().hex,
            "expires_at": timezone.now() + VERIFICATION_TOKEN_TTL,
        },
    )
    return token


def send_verification_email(user) -> None:
    """Create a token and email a verification link to the user."""
    token = create_verification_token(user)
    verify_url = settings.BASE_URL + reverse(
        "verify-email", kwargs={"token": token.token}
    )
    send_mail(
        subject="Verify your email on ODP",
        message=(
            f"Hi {user.username},\n\n"
            f"Please verify your email address by visiting:\n{verify_url}\n\n"
            "This link expires in 24 hours. If you didn't request this, ignore it."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
