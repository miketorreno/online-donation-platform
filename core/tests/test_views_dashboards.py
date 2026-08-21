from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.services import record_donation
from core.tests.test_models import make_campaign, make_user


def _donate(campaign, amount, donor=None, message=""):
    return record_donation(campaign=campaign, amount=amount, donor=donor, message=message)


class MyCampaignsViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(reverse("my-campaigns"))
        self.assertRedirects(resp, "/accounts/login/?next=/my/campaigns/")

    def test_lists_only_own_campaigns_with_correct_sums(self):
        funded = make_campaign(creator=self.alice, title="Alice Garden")
        untouched = make_campaign(creator=self.alice, title="Alice Tutoring")
        bob_campaign = make_campaign(creator=self.bob, title="Bob Shelter")
        _donate(funded, Decimal("10.00"), donor=self.bob)
        _donate(funded, Decimal("15.00"), donor=self.alice)
        _donate(bob_campaign, Decimal("99.00"), donor=self.alice)

        self.client.force_login(self.alice)
        resp = self.client.get(reverse("my-campaigns"))
        content = resp.content.decode()
        self.assertEqual(content.count("data-dashboard-campaign"), 2)
        self.assertContains(resp, "Alice Garden")
        self.assertContains(resp, "Alice Tutoring")
        self.assertNotContains(resp, "Bob Shelter")
        self.assertContains(resp, "$25.00")  # Alice Garden raised
        self.assertContains(resp, "$0.00")  # Alice Tutoring raised
        self.assertNotContains(resp, "$99.00")

    def test_status_chips_reflect_state(self):
        make_campaign(creator=self.alice, title="Active One")
        make_campaign(creator=self.alice, title="Paused One", is_active=False)
        make_campaign(
            creator=self.alice,
            title="Ended One",
            end_date=timezone.now().date() - timedelta(days=1),
        )
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("my-campaigns"))
        self.assertEqual(resp.content.decode().count("data-dashboard-campaign"), 3)
        self.assertContains(resp, ">Active</span>")
        self.assertContains(resp, ">Paused</span>")
        self.assertContains(resp, ">Ended</span>")

    def test_header_cta_links_to_create(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("my-campaigns"))
        self.assertContains(resp, f'href="{reverse("campaign-create")}"')


class MyDonationsViewTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.bob = make_user(username="bob")
        self.garden = make_campaign(creator=self.bob, title="Bob Garden")
        self.wells = make_campaign(creator=self.bob, title="Bob Wells")

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(reverse("my-donations"))
        self.assertRedirects(resp, "/accounts/login/?next=/my/donations/")

    def test_lists_own_donations_with_links_total_and_message(self):
        _donate(self.garden, Decimal("10.00"), donor=self.alice)
        _donate(self.wells, Decimal("15.00"), donor=self.alice, message="For the pups")
        _donate(self.garden, Decimal("50.00"), donor=self.bob)  # not alice's
        _donate(self.garden, Decimal("77.77"))  # anonymous, nobody's

        self.client.force_login(self.alice)
        resp = self.client.get(reverse("my-donations"))
        self.assertTemplateUsed(resp, "core/my_donations.html")
        self.assertContains(resp, "Bob Garden")
        self.assertContains(resp, f'href="{self.garden.get_absolute_url()}"')
        self.assertContains(resp, "Bob Wells")
        self.assertContains(resp, "$10.00")
        self.assertContains(resp, "$15.00")
        self.assertContains(resp, "$25.00")  # total given
        self.assertContains(resp, "For the pups")
        self.assertNotContains(resp, "$50.00")
        self.assertNotContains(resp, "$77.77")

    def test_dashboards_do_not_leak_between_users(self):
        _donate(self.garden, Decimal("50.00"), donor=self.bob)
        alice_private = make_campaign(creator=self.alice, title="Alice Private")
        _donate(alice_private, Decimal("10.00"), donor=self.alice)
        _donate(self.garden, Decimal("15.00"), donor=self.alice)

        self.client.force_login(self.bob)
        resp = self.client.get(reverse("my-donations"))
        self.assertContains(resp, "$50.00")  # bob's own gift
        self.assertNotContains(resp, "$15.00")  # alice's gifts are not his
        self.assertNotContains(resp, "Alice Private")

        campaigns_resp = self.client.get(reverse("my-campaigns"))
        content = campaigns_resp.content.decode()
        self.assertEqual(content.count("data-dashboard-campaign"), 2)
        self.assertNotContains(campaigns_resp, "Alice Private")
