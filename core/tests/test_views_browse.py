from decimal import Decimal
import re

from django.test import TestCase
from django.urls import reverse

from core.models import Campaign
from core.tests.test_models import make_campaign, make_user


def _card_titles(html):
    """Titles in rendered grid order (one h3 per campaign card)."""
    parts = html.split("data-campaign-card")[1:]
    return [re.search(r"line-clamp-2\">([^<]+)</h3>", part).group(1) for part in parts]


def _seed_campaigns(creator):
    """Create 12 campaigns in a fixed order; creation order == recency order."""
    specs = [
        ("Clean Water Wells", "emergency"),
        ("Wells for Schools", "education"),
        ("Community Garden", "environment"),
        ("Food Bank Drive", "community"),
        ("Tutoring Program", "education"),
        ("Dog Shelter Beds", "animals"),
        ("Tree Planting", "environment"),
        ("Youth Sports Gear", "sports"),
        ("Richest Rescue", "animals"),
        ("Neighborhood Cleanup", "community"),
        ("Zebra Fund", "arts"),
    ]
    created = {}
    for i, (title, category) in enumerate(specs):
        overrides: dict = dict(
            creator=creator,
            title=title,
            description=f"Support the {title.lower()} effort.",
            category=category,
        )
        if title == "Richest Rescue":
            overrides["current_amount"] = Decimal("9000.00")
        created[title] = make_campaign(**overrides)
    created["Closed Closet Sale"] = make_campaign(
        creator=creator,
        title="Closed Closet Sale",
        description="Support the closed closet sale effort.",
        is_active=False,
    )
    return created


class CampaignListViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.campaigns = _seed_campaigns(self.user)

    def test_home_renders_active_campaigns_paginated(self):
        resp = self.client.get(reverse("campaign-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/home.html")
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count("data-campaign-card"), 9)
        page2 = self.client.get(reverse("campaign-list") + "?page=2")
        self.assertEqual(page2.status_code, 200)
        self.assertEqual(page2.content.decode("utf-8").count("data-campaign-card"), 2)
        self.assertNotContains(page2, "Community Garden")

    def test_inactive_campaign_not_listed(self):
        resp = self.client.get(reverse("campaign-list"))
        self.assertNotContains(resp, "Closed Closet Sale")

    def test_q_narrows_to_matching_titles_only(self):
        resp = self.client.get(reverse("campaign-list") + "?q=wells")
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count("data-campaign-card"), 2)
        self.assertContains(resp, "Clean Water Wells")
        self.assertContains(resp, "Wells for Schools")
        self.assertNotContains(resp, "Community Garden")

    def test_category_filter_animals(self):
        resp = self.client.get(reverse("campaign-list") + "?category=animals")
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count("data-campaign-card"), 2)
        self.assertContains(resp, "Dog Shelter Beds")
        self.assertContains(resp, "Richest Rescue")
        self.assertNotContains(resp, "Clean Water Wells")

    def test_unknown_category_param_ignored(self):
        resp = self.client.get(reverse("campaign-list") + "?category=nonsense")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count("data-campaign-card"), 9)

    def test_sort_funded_orders_by_current_amount_desc(self):
        resp = self.client.get(reverse("campaign-list") + "?sort=funded")
        titles = _card_titles(resp.content.decode("utf-8"))
        self.assertEqual(titles[0], "Richest Rescue")

    def test_unknown_sort_falls_back_to_newest(self):
        resp = self.client.get(reverse("campaign-list") + "?sort=bogus")
        titles = _card_titles(resp.content.decode("utf-8"))
        self.assertEqual(titles[0], "Zebra Fund")

    def test_empty_state_when_nothing_matches(self):
        resp = self.client.get(reverse("campaign-list") + "?q=zzz-no-match-zzz")
        self.assertContains(resp, "No campaigns match your search")

    def test_pagination_absent_for_single_page(self):
        resp = self.client.get(reverse("campaign-list") + "?q=wells")
        self.assertNotContains(resp, 'aria-label="Pagination"')

    def test_nav_contains_explore_link(self):
        resp = self.client.get(reverse("campaign-list"))
        self.assertContains(resp, ">Explore</a>")

    def test_context_extras_and_active_pill_styling(self):
        resp = self.client.get(reverse("campaign-list") + "?category=animals&sort=funded")
        self.assertEqual(resp.context["active_category"], "animals")
        self.assertEqual(resp.context["active_sort"], "funded")
        self.assertEqual(list(resp.context["categories"]), Campaign.Category.choices)
        self.assertIn(
            "bg-pine-700 text-white",
            resp.content.decode("utf-8"),
            "active category pill should be highlighted",
        )
