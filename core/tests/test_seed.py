from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Campaign, Donation

EXPECTED_CATEGORIES = {
    "rebuild-maple-street-community-garden": "community",
    "emergency-vet-care-for-rescue-puppies": "animals",
    "laptops-for-linwood-middle-school": "education",
    "wildfire-relief-for-cedar-county": "emergency",
    "riverside-trail-restoration": "environment",
    "youth-soccer-scholarships": "sports",
    "community-mural-project": "arts",
    "free-dental-clinic-days": "medical",
}
ENDED_SLUGS = {"riverside-trail-restoration"}


class SeedDemoTests(TestCase):
    def test_seeds_demo_user_campaigns_and_donations(self):
        call_command("seed_demo")

        User = get_user_model()
        demo = User.objects.get(username="demo")
        self.assertEqual(demo.email, "demo@example.com")
        self.assertTrue(demo.check_password("demo-pass-1234"))

        self.assertEqual(Campaign.objects.count(), 8)
        for slug, category in EXPECTED_CATEGORIES.items():
            campaign = Campaign.objects.get(slug=slug)
            self.assertEqual(campaign.category, category)
            self.assertEqual(campaign.creator.username, "demo")

        for campaign in Campaign.objects.all():
            if campaign.slug in ENDED_SLUGS:
                continue
            self.assertGreater(campaign.current_amount, 0)
            self.assertTrue(campaign.donations.exists())

        # odd indexes -> demo user, even -> anonymous
        mural = Campaign.objects.get(slug="community-mural-project")
        donors = list(mural.donations.order_by("donated_at", "pk").values_list("donor__username", flat=True))
        self.assertEqual(donors[0], None)
        self.assertEqual(donors[1], "demo")

    def test_second_run_is_idempotent(self):
        call_command("seed_demo")
        first_count = Donation.objects.count()
        first_totals = {c.slug: c.current_amount for c in Campaign.objects.all()}

        out = _capture(call_command, "seed_demo")
        self.assertEqual(Campaign.objects.count(), 8)
        self.assertEqual(Donation.objects.count(), first_count)
        second_totals = {c.slug: c.current_amount for c in Campaign.objects.all()}
        self.assertEqual(first_totals, second_totals)
        self.assertIn("Seeded", out)

    def test_force_removes_stray_demo_campaign_with_duplicate_slug(self):
        call_command("seed_demo")
        demo = get_user_model().objects.get(username="demo")
        Campaign.objects.filter(slug="community-mural-project").delete()
        Campaign.objects.create(
            title="Stray Mural",
            slug="community-mural-project",
            description="A stray duplicate.",
            goal_amount="100.00",
            end_date=timezone.now().date() + timedelta(days=5),
            creator=demo,
        )
        self.assertEqual(Campaign.objects.count(), 8)
        self.assertEqual(Campaign.objects.get(slug="community-mural-project").title, "Stray Mural")

        call_command("seed_demo", "--force")
        self.assertEqual(Campaign.objects.count(), 8)
        mural = Campaign.objects.get(slug="community-mural-project")
        self.assertEqual(mural.title, "Community Mural Project")
        self.assertEqual(mural.category, "arts")
        self.assertGreater(mural.current_amount, 0)

    def test_force_spares_demo_campaigns_outside_seed_slugs(self):
        call_command("seed_demo")
        demo = get_user_model().objects.get(username="demo")
        Campaign.objects.create(
            title="Neighborhood Tool Library",
            slug="neighborhood-tool-library",
            description="A lending shelf for power tools.",
            goal_amount="500.00",
            end_date=timezone.now().date() + timedelta(days=10),
            creator=demo,
        )

        call_command("seed_demo", "--force")

        self.assertEqual(Campaign.objects.count(), 9)
        self.assertTrue(Campaign.objects.filter(slug="neighborhood-tool-library", creator=demo).exists())

    def test_force_reseeds_fresh_donations(self):
        call_command("seed_demo")
        before = Donation.objects.count()

        call_command("seed_demo", "--force")
        self.assertEqual(Donation.objects.count(), before)
        ended = Campaign.objects.get(slug="riverside-trail-restoration")
        self.assertEqual(ended.donations.count(), 0)
        self.assertEqual(ended.current_amount, 0)


def _capture(func, *args, **kwargs):
    from io import StringIO

    buf = StringIO()
    kwargs["stdout"] = buf
    func(*args, **kwargs)
    return buf.getvalue()
