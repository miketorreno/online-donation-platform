from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models import Campaign, Donation


def make_user(username="creator"):
    return get_user_model().objects.create_user(username=username, password="test-pass-123")


def make_campaign(**overrides):
    defaults = dict(
        title="Clean Water Wells",
        description="Drilling wells.",
        goal_amount=Decimal("500.00"),
        end_date=timezone.now().date() + timedelta(days=30),
    )
    defaults.update(overrides)
    if "creator" not in defaults:
        defaults["creator"] = make_user()
    return Campaign.objects.create(**defaults)


class CampaignSlugTests(TestCase):
    def test_slug_generated_from_title(self):
        c = make_campaign()
        self.assertEqual(c.slug, "clean-water-wells")

    def test_slug_collision_gets_numeric_suffix(self):
        c1 = make_campaign()
        c2 = make_campaign(title="Clean Water Wells!", creator=make_user(username="other"))
        self.assertEqual(c1.slug, "clean-water-wells")
        self.assertEqual(c2.slug, "clean-water-wells-2")

    def test_explicit_slug_preserved(self):
        c = make_campaign()
        c.slug = "custom"
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.slug, "custom")

    def test_category_default_and_choices(self):
        c = make_campaign()
        self.assertEqual(c.category, Campaign.Category.COMMUNITY)
        self.assertIn(("animals", "Animals"), Campaign.Category.choices)


class DonationModelTests(TestCase):
    def setUp(self):
        self.campaign = make_campaign()

    def test_message_blank_allowed(self):
        d = Donation.objects.create(
            campaign=self.campaign,
            amount=Decimal("25.00"),
            donor=None,
            message="",
        )
        self.assertEqual(d.message, "")
        self.assertIsNone(d.donor)

    def test_str_anonymous(self):
        d = Donation.objects.create(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertIn("Anonymous", str(d))
