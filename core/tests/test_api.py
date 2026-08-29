from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from core.models import Campaign, CampaignUpdate, Donation
from core.tests.test_models import make_campaign, make_user


class CampaignApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = make_user(username="creator")
        self.campaign = make_campaign(creator=self.creator)
        self.list_url = reverse("api:campaign-list")

    def _detail(self, name, **kwargs):
        return reverse(name, kwargs=kwargs)


class PublicApiTests(CampaignApiTests):
    def test_list_campaigns_paginated(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)
        self.assertEqual(resp.data["results"][0]["slug"], self.campaign.slug)
        supporter_count = resp.data["results"][0]["supporter_count"]
        self.assertEqual(supporter_count, 0)

    def test_search_filter(self):
        resp = self.client.get(self.list_url, {"q": "Water"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_retrieve_campaign(self):
        resp = self.client.get(self._detail("api:campaign-detail", slug=self.campaign.slug))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["slug"], self.campaign.slug)
        self.assertIn("percentage_raised", resp.data)
        self.assertIn("days_remaining", resp.data)

    def test_donations_public(self):
        Donation.objects.create(
            campaign=self.campaign, amount=Decimal("25.00"), donor=self.creator, message="hi"
        )
        resp = self.client.get(self._detail("api:campaign-donations", slug=self.campaign.slug))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["amount"], "25.00")

    def test_updates_list_public(self):
        CampaignUpdate.objects.create(campaign=self.campaign, title="T", body="B")
        resp = self.client.get(self._detail("api:campaign-updates", slug=self.campaign.slug))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 1)


class AuthApiTests(CampaignApiTests):
    def test_create_campaign_requires_auth(self):
        resp = self.client.post(
            reverse("api:campaign-create"),
            {"title": "New", "goal_amount": "100.00", "end_date": "2027-01-01"},
            format="json",
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_create_campaign_with_token(self):
        token = Token.objects.create(user=self.creator)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        resp = self.client.post(
            self._detail("api:campaign-create"),
            {
                "title": "New Campaign",
                "description": "d",
                "goal_amount": "100.00",
                "end_date": "2027-01-01",
                "category": "education",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Campaign.objects.filter(title="New Campaign").exists())

    def test_token_auth_endpoint(self):
        self.creator.set_password("pass12345")
        self.creator.save()
        resp = self.client.post(
            reverse("api:auth-token"),
            {"username": "creator", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)

    def test_schema_renders(self):
        resp = self.client.get(reverse("api:schema"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"openapi", resp.content.lower())


class OwnershipApiTests(CampaignApiTests):
    def _auth_as(self, user):
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def test_non_owner_cannot_edit(self):
        other = make_user(username="other")
        self._auth_as(other)
        resp = self.client.patch(
            self._detail("api:campaign-edit", slug=self.campaign.slug),
            {"description": "x"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_edit(self):
        self._auth_as(self.creator)
        resp = self.client.patch(
            self._detail("api:campaign-edit", slug=self.campaign.slug),
            {"description": "updated"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_owner_can_create_update(self):
        self._auth_as(self.creator)
        resp = self.client.post(
            self._detail("api:campaign-update-create", slug=self.campaign.slug),
            {"title": "U", "body": "B"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_non_owner_cannot_create_update(self):
        other = make_user(username="other")
        self._auth_as(other)
        resp = self.client.post(
            self._detail("api:campaign-update-create", slug=self.campaign.slug),
            {"title": "U", "body": "B"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_stats_owner_only(self):
        url = self._detail("api:campaign-stats", slug=self.campaign.slug)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (401, 403))
        self._auth_as(self.creator)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_raised", resp.data)
