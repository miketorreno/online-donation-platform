"""Tests for Celery background tasks (foundation).

Tasks are executed synchronously via `.apply()` (eager) so they can be tested
without a live broker/worker.
"""
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import (
    Campaign,
    CampaignUpdate,
    Donation,
    Notification,
    SavedCampaign,
)
from core.tasks import (
    check_campaign_lifecycle,
    notify_update_posted,
    ping,
    send_donation_receipt_task,
)
from core.tests.test_models import make_campaign, make_user


class PingTaskTests(TestCase):
    def test_ping_returns_pong(self):
        result = ping.apply(args=["hello"])
        self.assertEqual(result.get(), "pong:hello")

    def test_ping_without_payload(self):
        result = ping.apply()
        self.assertEqual(result.get(), "pong:")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DonationReceiptTaskTests(TestCase):
    def test_sends_receipt_to_donor(self):
        donor = make_user(username="donor")
        donor.email = "donor@example.com"
        donor.save()
        campaign = make_campaign(creator=make_user(username="creator"))
        donation = Donation.objects.create(
            campaign=campaign,
            amount=Decimal("25.00"),
            donor=donor,
            transaction_id="SIM-x",
        )
        send_donation_receipt_task.apply(args=[donation.pk])
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_donation_is_noop(self):
        result = send_donation_receipt_task.apply(args=[999999])
        self.assertEqual(result.get(), None)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotifyUpdatePostedTests(TestCase):
    def test_notifies_followers(self):
        follower = make_user(username="follower")
        follower.email = "follower@example.com"
        follower.save()
        creator = make_user(username="creator")
        campaign = make_campaign(creator=creator)
        SavedCampaign.objects.create(user=follower, campaign=campaign)
        update = CampaignUpdate.objects.create(
            campaign=campaign, title="Update", body="Body"
        )
        notify_update_posted.apply(args=[update.pk])
        self.assertEqual(len(mail.outbox), 1)
        notification = Notification.objects.get(
            recipient=follower, kind=Notification.Kind.UPDATE_POSTED
        )
        self.assertEqual(notification.update, update)

    def test_skips_followers_not_opted_in(self):
        follower = make_user(username="follower")
        follower.email = "follower@example.com"
        follower.save()
        follower.profile.receives_email_updates = False
        follower.profile.save(update_fields=["receives_email_updates"])
        campaign = make_campaign(creator=make_user(username="creator"))
        SavedCampaign.objects.create(user=follower, campaign=campaign)
        update = CampaignUpdate.objects.create(
            campaign=campaign, title="U", body="B"
        )
        notify_update_posted.apply(args=[update.pk])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            Notification.objects.filter(
                recipient=follower, kind=Notification.Kind.UPDATE_POSTED
            ).count(),
            1,
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CheckCampaignLifecycleTests(TestCase):
    def test_notifies_when_funded(self):
        today = timezone.now().date()
        follower = make_user(username="follower")
        follower.email = "follower@example.com"
        follower.save()
        creator = make_user(username="creator")
        campaign = make_campaign(
            creator=creator,
            goal_amount=Decimal("100.00"),
            current_amount=Decimal("100.00"),
            end_date=today + timedelta(days=30),
        )
        SavedCampaign.objects.create(user=follower, campaign=campaign)
        result = check_campaign_lifecycle.apply().get()
        self.assertEqual(result, 1)
        campaign.refresh_from_db()
        self.assertTrue(campaign.funded_notified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=follower, kind=Notification.Kind.CAMPAIGN_FUNDED
            ).exists()
        )

    def test_notifies_when_expiring_soon(self):
        today = timezone.now().date()
        follower = make_user(username="follower")
        follower.email = "follower@example.com"
        follower.save()
        campaign = make_campaign(
            creator=make_user(username="creator"),
            goal_amount=Decimal("500.00"),
            end_date=today + timedelta(days=2),
        )
        SavedCampaign.objects.create(user=follower, campaign=campaign)
        result = check_campaign_lifecycle.apply().get()
        self.assertEqual(result, 1)
        campaign.refresh_from_db()
        self.assertTrue(campaign.expiring_notified)
        self.assertTrue(
            Notification.objects.filter(
                recipient=follower, kind=Notification.Kind.EXPIRING_SOON
            ).exists()
        )

    def test_idempotent_no_double_notification(self):
        today = timezone.now().date()
        follower = make_user(username="follower")
        follower.email = "follower@example.com"
        follower.save()
        campaign = make_campaign(
            creator=make_user(username="creator"),
            goal_amount=Decimal("100.00"),
            current_amount=Decimal("100.00"),
            end_date=today + timedelta(days=30),
            funded_notified=True,
        )
        SavedCampaign.objects.create(user=follower, campaign=campaign)
        result = check_campaign_lifecycle.apply().get()
        self.assertEqual(result, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Notification.objects.filter(campaign=campaign).count(), 0)
