from django.test import TestCase
from django.urls import reverse

from core.models import Notification
from core.tests.test_models import make_campaign, make_user


class NotificationViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=make_user(username="creator"))
        self.notification = Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.UPDATE_POSTED,
            campaign=self.campaign,
            message="New update on a campaign",
        )

    def test_requires_login(self):
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 302)

    def test_inbox_shows_own_notifications_only(self):
        Notification.objects.create(
            recipient=self.bob,
            kind=Notification.Kind.CAMPAIGN_FUNDED,
            campaign=self.campaign,
            message="Bob's message",
        )
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("notifications"))
        self.assertContains(resp, "New update on a campaign")
        self.assertNotContains(resp, "Bob's message")

    def test_unread_count_in_context(self):
        self.client.force_login(self.alice)
        Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.EXPIRING_SOON,
            campaign=self.campaign,
            message="Closing soon",
        )
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.context["unread_count"], 2)

    def test_mark_read(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("notification-read", kwargs={"pk": self.notification.pk})
        )
        self.assertRedirects(resp, reverse("notifications"))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.read)

    def test_mark_all_read(self):
        self.client.force_login(self.alice)
        Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.CAMPAIGN_FUNDED,
            campaign=self.campaign,
            message="Funded",
        )
        self.client.post(reverse("notification-read-all"))
        self.assertEqual(
            self.alice.notifications.filter(read=False).count(), 0
        )

    def test_cannot_mark_others_notification(self):
        self.client.force_login(self.bob)
        resp = self.client.post(
            reverse("notification-read", kwargs={"pk": self.notification.pk})
        )
        self.assertEqual(resp.status_code, 404)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.read)


class UnreadBadgeTests(TestCase):
    def test_badge_shown_for_authenticated_user(self):
        user = make_user(username="alice")
        self.client.force_login(user)
        Notification.objects.create(
            recipient=user,
            kind=Notification.Kind.UPDATE_POSTED,
            message="Test",
        )
        resp = self.client.get(reverse("campaign-list"))
        self.assertContains(resp, "Notifications")
        self.assertContains(resp, "1</span>")
