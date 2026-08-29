"""Email sending helpers (transactional emails).

All senders go through Django's mail backend (`EMAIL_BACKEND`). Locally the
default is the file backend, so no SMTP is required in dev/CI.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
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


def _campaign_url(campaign) -> str:
    return settings.BASE_URL + campaign.get_absolute_url()


def _render(subject, template, context, recipient) -> None:
    """Render a template and send a plain-text email."""
    body = render_to_string(template, context).strip()
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
    )


def send_donation_receipt(donation) -> None:
    """Send a receipt to a donor (no-op for anonymous donations)."""
    if donation.donor is None or not donation.donor.email:
        return
    _render(
        subject=f"Your {donation.amount} gift to {donation.campaign.title}",
        template="core/emails/donation_receipt.txt",
        context={
            "donation": donation,
            "campaign": donation.campaign,
            "campaign_url": _campaign_url(donation.campaign),
        },
        recipient=donation.donor.email,
    )


def send_campaign_funded_email(campaign, recipient_email: str) -> None:
    """Notify a saved/following user that a campaign reached its goal."""
    _render(
        subject=f"{campaign.title} reached its goal!",
        template="core/emails/campaign_funded.txt",
        context={
            "campaign": campaign,
            "campaign_url": _campaign_url(campaign),
        },
        recipient=recipient_email,
    )


def send_expiring_soon_email(campaign, recipient_email: str) -> None:
    """Notify a saved/following user that a campaign is about to expire."""
    _render(
        subject=f"{campaign.title} is closing soon",
        template="core/emails/expiring_soon.txt",
        context={
            "campaign": campaign,
            "campaign_url": _campaign_url(campaign),
        },
        recipient=recipient_email,
    )


def send_update_posted_email(campaign, update, recipient_email: str) -> None:
    """Notify a saved/following user of a new campaign update."""
    _render(
        subject=f"New update on {campaign.title}: {update.title}",
        template="core/emails/update_posted.txt",
        context={
            "campaign": campaign,
            "update": update,
            "campaign_url": _campaign_url(campaign),
        },
        recipient=recipient_email,
    )
