from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Campaign, Donation
from core.tests.test_models import make_campaign, make_user

END_DATE = (timezone.now().date() + timedelta(days=20)).isoformat()

CAMPAIGN_DATA = {
    "title": "New Rooftop Bees",
    "description": "Hives on the library roof.",
    "category": "environment",
    "goal_amount": "750.00",
    "end_date": END_DATE,
}

EDITED_DATA = dict(CAMPAIGN_DATA, title="A Very Different Title")


class CampaignCreateViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")

    def test_anonymous_create_redirects_to_login(self):
        resp = self.client.get(reverse("campaign-create"))
        self.assertRedirects(resp, "/accounts/login/?next=/campaigns/new/")

    def test_logged_in_get_renders_form(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("campaign-create"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/campaign_form.html")
        for name in ("title", "description", "category", "goal_amount", "end_date"):
            self.assertContains(resp, f'name="{name}"')

    def test_valid_post_creates_campaign_for_creator_and_redirects_to_detail(self):
        self.client.force_login(self.alice)
        resp = self.client.post(reverse("campaign-create"), CAMPAIGN_DATA, follow=True)
        campaign = Campaign.objects.get(title="New Rooftop Bees")
        self.assertEqual(campaign.creator, self.alice)
        self.assertEqual(campaign.slug, "new-rooftop-bees")
        self.assertEqual(campaign.goal_amount, Decimal("750.00"))
        self.assertRedirects(resp, campaign.get_absolute_url())
        self.assertContains(resp, "Campaign created.")


class CampaignUpdateViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=self.alice)
        self.edit_url = reverse("campaign-edit", kwargs={"slug": self.campaign.slug})

    def test_owner_get_edit_renders_form(self):
        self.client.force_login(self.alice)
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/campaign_form.html")
        self.assertContains(resp, 'value="Clean Water Wells"')

    def test_owner_edit_changes_title_and_keeps_slug_stable(self):
        self.client.force_login(self.alice)
        old_slug = self.campaign.slug
        resp = self.client.post(self.edit_url, EDITED_DATA)
        self.campaign.refresh_from_db()
        self.assertRedirects(resp, reverse("campaign-detail", kwargs={"slug": old_slug}))
        self.assertEqual(self.campaign.title, "A Very Different Title")
        self.assertEqual(self.campaign.slug, old_slug)

    def test_owner_edit_shows_updated_message(self):
        self.client.force_login(self.alice)
        resp = self.client.post(self.edit_url, EDITED_DATA, follow=True)
        self.assertContains(resp, "Campaign updated.")

    def test_anonymous_get_edit_redirects_to_login(self):
        resp = self.client.get(self.edit_url)
        self.assertRedirects(resp, f"/accounts/login/?next={self.edit_url}")

    def test_edit_by_other_user_is_403(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)
        resp = self.client.post(self.edit_url, EDITED_DATA)
        self.assertEqual(resp.status_code, 403)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.title, "Clean Water Wells")


class CampaignDeleteViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=self.alice)
        Donation.objects.create(
            campaign=self.campaign, amount=Decimal("25.00"), donor=None, message=""
        )
        self.delete_url = reverse(
            "campaign-delete", kwargs={"slug": self.campaign.slug}
        )

    def test_delete_confirm_warns_about_donation_records(self):
        self.client.force_login(self.alice)
        resp = self.client.get(self.delete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/campaign_confirm_delete.html")
        self.assertContains(resp, "Deleting removes its donation records too.")

    def test_owner_delete_removes_campaign_and_its_donations(self):
        self.client.force_login(self.alice)
        resp = self.client.post(self.delete_url)
        self.assertRedirects(resp, reverse("my-campaigns"))
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Donation.objects.count(), 0)

    def test_owner_delete_shows_deleted_message(self):
        self.client.force_login(self.alice)
        resp = self.client.post(self.delete_url, follow=True)
        self.assertContains(resp, "Campaign deleted.")

    def test_anonymous_get_delete_redirects_to_login(self):
        resp = self.client.get(self.delete_url)
        self.assertRedirects(resp, f"/accounts/login/?next={self.delete_url}")

    def test_delete_by_other_user_is_403(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(self.delete_url).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assertEqual(Campaign.objects.count(), 1)


class ToggleActiveViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=self.alice)
        self.toggle_url = reverse(
            "campaign-toggle-active", kwargs={"slug": self.campaign.slug}
        )

    def test_toggle_get_is_not_allowed(self):
        self.client.force_login(self.alice)
        resp = self.client.get(self.toggle_url)
        self.assertEqual(resp.status_code, 405)
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_active)

    def test_toggle_post_by_owner_flips_state_and_redirects_to_detail(self):
        self.client.force_login(self.alice)
        resp = self.client.post(self.toggle_url, follow=True)
        self.campaign.refresh_from_db()
        self.assertFalse(self.campaign.is_active)
        self.assertRedirects(
            resp, reverse("campaign-detail", kwargs={"slug": self.campaign.slug})
        )
        self.assertContains(resp, "Campaign paused.")

        resp = self.client.post(self.toggle_url, follow=True)
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_active)
        self.assertContains(resp, "Campaign resumed.")

    def test_toggle_post_by_other_user_is_403(self):
        self.client.force_login(self.bob)
        resp = self.client.post(self.toggle_url)
        self.assertEqual(resp.status_code, 403)
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_active)


class NavBarTests(TestCase):
    def setUp(self):
        self.user = make_user(username="alice")

    def test_start_campaign_link_visible_when_logged_out(self):
        resp = self.client.get(reverse("campaign-list"))
        self.assertContains(resp, ">Start a campaign</a>")
        self.assertContains(resp, f'href="{reverse("campaign-create")}"')
        self.assertNotContains(resp, "/my/campaigns/")

    def test_authenticated_dropdown_has_dashboard_links(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("campaign-list"))
        self.assertContains(resp, ">My campaigns</a>")
        self.assertContains(resp, f'href="{reverse("my-campaigns")}"')
        self.assertContains(resp, ">My donations</a>")
        self.assertContains(resp, f'href="{reverse("my-donations")}"')
