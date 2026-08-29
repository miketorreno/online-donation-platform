"""Celery background tasks for the core app.

Tasks must be idempotent and accept primary keys (never ORM instances), since
they may execute asynchronously after the request that enqueued them.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .emails import (
    send_donation_receipt,
    send_expiring_soon_email,
    send_update_posted_email,
)
from .models import Campaign, CampaignUpdate, Donation, Notification

logger = logging.getLogger(__name__)


@shared_task(name="core.ping")
def ping(payload: str = "") -> str:
    """Smoke-test task proving the broker/worker round-trip works."""
    logger.info("core.ping received payload=%r", payload)
    return f"pong:{payload}"


@shared_task(name="core.send_donation_receipt")
def send_donation_receipt_task(donation_pk: int) -> None:
    """Email a receipt for a donation (idempotent; skips anonymous donors)."""
    donation = Donation.objects.select_related("donor", "campaign").filter(pk=donation_pk).first()
    if donation is None:
        logger.warning("send_donation_receipt: donation %s not found", donation_pk)
        return
    send_donation_receipt(donation)


@shared_task(name="core.notify_update_posted")
def notify_update_posted(update_pk: int) -> None:
    """Email + notify followers of a campaign when an update is posted."""
    update = (
        CampaignUpdate.objects.select_related("campaign").filter(pk=update_pk).first()
    )
    if update is None:
        logger.warning("notify_update_posted: update %s not found", update_pk)
        return
    campaign = update.campaign
    followers = _campaign_followers(campaign)
    for profile in followers:
        if profile.receives_email_updates and profile.user.email:
            send_update_posted_email(campaign, update, profile.user.email)
        Notification.objects.create(
            recipient=profile.user,
            kind=Notification.Kind.UPDATE_POSTED,
            campaign=campaign,
            update=update,
            message=f"New update on {campaign.title}: {update.title}",
        )


def _campaign_followers(campaign):
    """Profiles of users who saved the campaign, email-opted-in."""
    from .models import SavedCampaign

    user_ids = SavedCampaign.objects.filter(campaign=campaign).values_list("user_id", flat=True)
    from .models import Profile

    return Profile.objects.filter(user_id__in=list(user_ids)).select_related("user")


@shared_task(name="core.check_campaign_lifecycle")
def check_campaign_lifecycle(expiring_days: int = 3) -> int:
    """Send funded / expiring-soon notifications for active campaigns.

    Idempotent: each campaign is only notified once per state via the
    `funded_notified` / `expiring_notified` flags.
    """
    now = timezone.now().date()
    sent = 0
    for campaign in Campaign.objects.filter(is_active=True):
        # Newly funded: only notify if it crossed its goal but hasn't been
        # flagged yet (avoids re-notifying campaigns that have been funded
        # for a while).
        if (
            not campaign.funded_notified
            and campaign.current_amount >= campaign.goal_amount
        ):
            _notify_campaign_state(campaign, Notification.Kind.CAMPAIGN_FUNDED)
            campaign.funded_notified = True
            campaign.save(update_fields=["funded_notified", "updated_at"])
            sent += 1
        elif (
            not campaign.expiring_notified
            and campaign.end_date - now <= timedelta(days=expiring_days)
            and campaign.end_date >= now
        ):
            _notify_campaign_state(campaign, Notification.Kind.EXPIRING_SOON)
            campaign.expiring_notified = True
            campaign.save(update_fields=["expiring_notified", "updated_at"])
            sent += 1
    return sent


def _notify_campaign_state(campaign, kind) -> None:
    from .emails import send_campaign_funded_email

    if kind == Notification.Kind.CAMPAIGN_FUNDED:
        message = f"{campaign.title} reached its goal of ${campaign.goal_amount}"
    else:
        message = f"{campaign.title} is closing soon"
    followers = _campaign_followers(campaign)
    for profile in followers:
        if profile.receives_email_updates and profile.user.email:
            if kind == Notification.Kind.CAMPAIGN_FUNDED:
                send_campaign_funded_email(campaign, profile.user.email)
            else:
                send_expiring_soon_email(campaign, profile.user.email)
        Notification.objects.create(
            recipient=profile.user,
            kind=kind,
            campaign=campaign,
            message=message,
        )
