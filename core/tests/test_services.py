from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from core.models import Campaign
from core.services import DonationError, record_donation
from core.tests.test_models import make_campaign


class RecordDonationTests(TestCase):
    def setUp(self):
        self.campaign = make_campaign(goal_amount=Decimal("1000.00"))

    def test_successful_donation_updates_total_and_returns_record(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("25.00"))
        self.assertEqual(d.amount, Decimal("25.00"))
        self.assertTrue(d.transaction_id.startswith("SIM-"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("25.00"))

    def test_two_donations_accumulate(self):
        record_donation(campaign=self.campaign, amount=Decimal("10.00"))
        record_donation(campaign=self.campaign, amount=Decimal("15.50"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("25.50"))

    def test_anonymous_donor_allowed(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertIsNone(d.donor)

    def test_message_is_stripped(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("5.00"), message="  go team  ")
        self.assertEqual(d.message, "go team")

    def test_minimum_amount_enforced(self):
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("0.99"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("0.00"))

    def test_inactive_campaign_rejected(self):
        self.campaign.is_active = False
        self.campaign.save()
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("10.00"))

    def test_ended_campaign_rejected(self):
        self.campaign.end_date = timezone.now().date() - timedelta(days=1)
        self.campaign.save()
        with self.assertRaises(DonationError):
            record_donation(campaign=self.campaign, amount=Decimal("10.00"))

    def test_sub_cent_amount_is_quantized_in_stored_amount_and_total(self):
        d = record_donation(campaign=self.campaign, amount=Decimal("25.555"))
        self.assertEqual(d.amount, Decimal("25.56"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("25.56"))

    def test_sub_cent_donations_accumulate_without_drift(self):
        record_donation(campaign=self.campaign, amount=Decimal("1.005"))
        record_donation(campaign=self.campaign, amount=Decimal("1.005"))
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.current_amount, Decimal("2.02"))

    def test_transaction_ids_unique(self):
        a = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        b = record_donation(campaign=self.campaign, amount=Decimal("5.00"))
        self.assertNotEqual(a.transaction_id, b.transaction_id)
