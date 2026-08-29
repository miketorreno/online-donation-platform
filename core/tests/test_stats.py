from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Donation
from core.tests.test_models import make_campaign, make_user


class CampaignStatsViewTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="other")
        self.campaign = make_campaign(creator=self.owner)
        self.url = reverse("campaign-stats", kwargs={"slug": self.campaign.slug})

    def _donate(self, amount, donor=None, message="", when=None):
        donation = Donation.objects.create(
            campaign=self.campaign,
            amount=amount,
            donor=donor,
            message=message,
        )
        if when is not None:
            Donation.objects.filter(pk=donation.pk).update(donated_at=when)
        return donation

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login", resp.url)

    def test_non_owner_forbidden(self):
        self.client.force_login(self.other)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_owner_sees_aggregates(self):
        self.client.force_login(self.owner)
        supporter = make_user(username="supporter")
        self._donate(Decimal("10.00"), donor=supporter, message="Go team!")
        self._donate(Decimal("30.00"), donor=None)
        self._donate(Decimal("20.00"), donor=supporter)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_raised"], Decimal("60.00"))
        self.assertEqual(resp.context["average_donation"], Decimal("20.00"))
        self.assertEqual(resp.context["maximum_donation"], Decimal("30.00"))
        self.assertEqual(resp.context["donation_count"], 3)
        self.assertEqual(resp.context["supporter_count"], 1)
        self.assertEqual(resp.context["with_message_count"], 1)
        self.assertEqual(resp.context["without_message_count"], 2)

    def test_trend_is_daily_cumulative_ordered(self):
        self.client.force_login(self.owner)
        base = timezone.now()
        self._donate(Decimal("10.00"), when=base)
        self._donate(Decimal("20.00"), when=base + timedelta(days=1))
        resp = self.client.get(self.url)
        trend = resp.context["trend"]
        self.assertEqual(len(trend), 2)
        self.assertTrue(trend[1]["cumulative"] <= trend[0]["cumulative"])

    def test_top_supporters_ordered(self):
        self.client.force_login(self.owner)
        big = make_user(username="big")
        small = make_user(username="small")
        self._donate(Decimal("5.00"), donor=small)
        self._donate(Decimal("50.00"), donor=big)
        resp = self.client.get(self.url)
        supporters = resp.context["top_supporters"]
        self.assertEqual(list(supporters)[0]["donor__username"], "big")

    def test_empty_campaign(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_raised"], Decimal("0.00"))
        self.assertEqual(resp.context["donation_count"], 0)
        self.assertEqual(resp.context["trend"], [])
        self.assertEqual(list(resp.context["top_supporters"]), [])


class CampaignStatsExportTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="other")
        self.campaign = make_campaign(creator=self.owner)
        self.url = reverse("campaign-stats-export", kwargs={"slug": self.campaign.slug})

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_non_owner_forbidden(self):
        self.client.force_login(self.other)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_owner_exports_csv(self):
        self.client.force_login(self.owner)
        donor = make_user(username="donor")
        Donation.objects.create(
            campaign=self.campaign, amount=Decimal("25.00"), donor=donor, message="Thanks"
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        content = resp.content.decode()
        self.assertIn("donor", content)
        self.assertIn("25.00", content)
