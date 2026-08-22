from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Donation
from core.tests.test_models import make_campaign, make_user


class DonateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.campaign = make_campaign(creator=self.user)
        self.url = reverse("campaign-donate", kwargs={"slug": self.campaign.slug})
        self.detail_url = reverse("campaign-detail", kwargs={"slug": self.campaign.slug})

    def test_donate_page_get_renders(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="id_amount"')
        self.assertContains(resp, "Complete gift")

    def test_post_valid_anonymous_creates_donation(self):
        resp = self.client.post(self.url, {"amount": "40.00"})
        self.assertRedirects(resp, self.detail_url, fetch_redirect_response=False)
        donation = Donation.objects.get()
        self.assertEqual(donation.amount, Decimal("40.00"))
        self.assertIsNone(donation.donor)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("40.00"))
        followed = self.client.get(self.detail_url)
        self.assertContains(followed, "Thank you! Your $40.00 gift")

    def test_post_valid_authed_attaches_donor(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {"amount": "20.00", "message": "go team"})
        self.assertRedirects(resp, self.detail_url, fetch_redirect_response=False)
        donation = Donation.objects.get()
        self.assertEqual(donation.donor, self.user)

    def test_post_invalid_negative_shows_error(self):
        resp = self.client.post(self.url, {"amount": "0.50"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Minimum donation")
        self.assertFalse(Donation.objects.exists())

    def test_post_to_ended_redirects_with_error(self):
        ended = make_campaign(
            title="Past Push",
            creator=self.user,
            end_date=timezone.now().date() - timedelta(days=1),
        )
        url = reverse("campaign-donate", kwargs={"slug": ended.slug})
        detail_url = reverse("campaign-detail", kwargs={"slug": ended.slug})
        resp = self.client.post(url, {"amount": "25.00"})
        self.assertRedirects(resp, detail_url, fetch_redirect_response=False)
        followed = self.client.get(detail_url)
        self.assertContains(followed, "not accepting donations")
        self.assertFalse(Donation.objects.exists())

    def test_preset_buttons_present(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "$25")
