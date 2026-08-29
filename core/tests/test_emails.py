from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings

from core.emails import (
    send_campaign_funded_email,
    send_donation_receipt,
    send_expiring_soon_email,
    send_update_posted_email,
)
from core.models import CampaignUpdate, Donation
from core.tests.test_models import make_campaign, make_user


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailSenderTests(TestCase):
    def setUp(self):
        self.donor = make_user(username="donor")
        self.donor.email = "donor@example.com"
        self.donor.save()
        self.campaign = make_campaign(creator=make_user(username="creator"))

    def test_send_donation_receipt(self):
        donation = Donation.objects.create(
            campaign=self.campaign,
            amount=Decimal("25.00"),
            donor=self.donor,
            transaction_id="SIM-x",
        )
        send_donation_receipt(donation)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("donor@example.com", mail.outbox[0].to)
        self.assertIn("$25.00", mail.outbox[0].body)

    def test_send_donation_receipt_skips_anonymous(self):
        donation = Donation.objects.create(
            campaign=self.campaign, amount=Decimal("25.00"), donor=None
        )
        send_donation_receipt(donation)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_campaign_funded_email(self):
        send_campaign_funded_email(self.campaign, self.donor.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reached its goal", mail.outbox[0].subject)

    def test_send_expiring_soon_email(self):
        send_expiring_soon_email(self.campaign, self.donor.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("closing soon", mail.outbox[0].subject)

    def test_send_update_posted_email(self):
        update = CampaignUpdate.objects.create(
            campaign=self.campaign, title="Hello", body="World"
        )
        send_update_posted_email(self.campaign, update, self.donor.email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hello", mail.outbox[0].subject)
