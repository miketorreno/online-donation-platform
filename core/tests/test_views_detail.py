from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.services import record_donation
from core.tests.test_models import make_campaign, make_user


class CampaignDetailViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.campaign = make_campaign(creator=self.user)
        self.url = reverse("campaign-detail", kwargs={"slug": self.campaign.slug})

    def test_detail_renders_title_progress_and_supporters(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.campaign.title)
        self.assertContains(resp, "$500.00")
        self.assertContains(resp, "Give now")

    def test_signature_percentage_present(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "text-7xl")

    def test_supporters_wall_lists_recent_capped_at_ten(self):
        fan = make_user(username="latestfan")
        for _ in range(12):
            record_donation(campaign=self.campaign, amount=Decimal("5.00"), donor=fan)
        resp = self.client.get(self.url)
        self.assertContains(resp, "latestfan")
        self.assertEqual(resp.content.decode("utf-8").count("data-supporter-row"), 10)

    def test_empty_wall_message(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "Be the first")

    def test_ended_campaign_shows_closed_chip(self):
        ended = make_campaign(
            title="Past Push",
            creator=self.user,
            end_date=timezone.now().date() - timedelta(days=1),
        )
        resp = self.client.get(reverse("campaign-detail", kwargs={"slug": ended.slug}))
        self.assertContains(resp, "has ended")
        self.assertNotContains(resp, "Give now")

    def test_unknown_slug_404(self):
        resp = self.client.get("/campaigns/does-not-exist/")
        self.assertEqual(resp.status_code, 404)

    def test_get_absolute_url(self):
        c = make_campaign(creator=self.user)
        self.assertEqual(c.get_absolute_url(), f"/campaigns/{c.slug}/")
