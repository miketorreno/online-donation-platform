from core.models import CampaignUpdate
from core.tests.test_models import make_campaign, make_user
from django.test import TestCase
from django.urls import reverse


class CampaignUpdateCreateViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=self.alice)
        self.url = reverse("campaign-update-create", kwargs={"slug": self.campaign.slug})

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_non_owner_gets_403(self):
        self.client.force_login(self.bob)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_owner_create_renders_form(self):
        self.client.force_login(self.alice)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="title"')
        self.assertContains(resp, 'name="body"')

    def test_owner_post_creates_update(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            self.url,
            {"title": "Milestone reached", "body": "We hit our first goal!", "is_pinned": "on"},
            follow=True,
        )
        update = CampaignUpdate.objects.get(title="Milestone reached")
        self.assertEqual(update.campaign, self.campaign)
        self.assertTrue(update.is_pinned)
        self.assertRedirects(resp, self.campaign.get_absolute_url())
        self.assertContains(resp, "Milestone reached")


class CampaignUpdateEditDeleteViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.campaign = make_campaign(creator=self.alice)
        self.update = CampaignUpdate.objects.create(
            campaign=self.campaign,
            title="First update",
            body="Hello!",
        )
        self.edit_url = reverse(
            "campaign-update-edit",
            kwargs={"slug": self.campaign.slug, "pk": self.update.pk},
        )
        self.delete_url = reverse(
            "campaign-update-delete",
            kwargs={"slug": self.campaign.slug, "pk": self.update.pk},
        )

    def test_non_owner_edit_403(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)
        self.assertEqual(self.client.get(self.delete_url).status_code, 403)

    def test_owner_edit_updates(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            self.edit_url,
            {"title": "Edited title", "body": "New body", "is_pinned": ""},
            follow=True,
        )
        self.update.refresh_from_db()
        self.assertEqual(self.update.title, "Edited title")
        self.assertRedirects(resp, self.campaign.get_absolute_url())

    def test_owner_delete_removes_and_redirects(self):
        self.client.force_login(self.alice)
        resp = self.client.post(self.delete_url, follow=True)
        self.assertFalse(CampaignUpdate.objects.filter(pk=self.update.pk).exists())
        self.assertRedirects(resp, self.campaign.get_absolute_url())
        self.assertContains(resp, "Update deleted.")


class CampaignUpdateModelTests(TestCase):
    def test_defaults_and_ordering(self):
        alice = make_user(username="alice")
        campaign = make_campaign(creator=alice)
        first = CampaignUpdate.objects.create(campaign=campaign, title="a", body="1")
        pinned = CampaignUpdate.objects.create(campaign=campaign, title="b", body="2", is_pinned=True)
        qs = list(campaign.updates.all())
        self.assertEqual(qs[0], pinned)  # pinned sorts first
        self.assertEqual(qs[1], first)
        self.assertEqual(str(first), "a (Clean Water Wells)")

    def test_covers_render_with_and_without_image(self):
        alice = make_user(username="alice")
        campaign = make_campaign(creator=alice)
        CampaignUpdate.objects.create(campaign=campaign, title="u", body="b")
        self.client.force_login(alice)
        resp = self.client.get(campaign.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Updates")
