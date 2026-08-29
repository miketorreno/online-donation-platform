import io
import csv
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import EmailVerificationToken, Profile, SavedCampaign
from core.tests.test_models import make_campaign, make_user

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProfileTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")

    def test_profile_autocreated_on_user_creation(self):
        self.assertTrue(Profile.objects.filter(user=self.alice).exists())
        self.assertFalse(self.alice.profile.email_verified)
        self.assertTrue(self.alice.profile.receives_email_updates)

    def test_profile_view_requires_login(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 302)

    def test_profile_view_renders(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Edit profile")

    def test_profile_update_saves_fields(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("profile-edit"),
            {
                "display_name": "Alice Wonder",
                "bio": "Community organizer.",
                "timezone": "America/New_York",
                "receives_email_updates": "on",
            },
            follow=True,
        )
        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.display_name, "Alice Wonder")
        self.assertEqual(self.alice.profile.bio, "Community organizer.")
        self.assertEqual(self.alice.profile.timezone, "America/New_York")
        self.assertTrue(self.alice.profile.receives_email_updates)
        self.assertContains(resp, "Profile updated.")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationTests(TestCase):
    def test_signup_creates_token_and_sends_email(self):
        resp = self.client.post(
            reverse("signup"),
            {
                "username": "newbie",
                "email": "newbie@example.com",
                "password1": "VeRy-Str0ng-pass",
                "password2": "VeRy-Str0ng-pass",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newbie")
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("newbie@example.com", mail.outbox[0].to)
        self.assertIn("verify your email", mail.outbox[0].subject.lower())

    def test_verify_valid_token_marks_verified(self):
        user = make_user(username="kin")
        token = EmailVerificationToken.objects.create(
            user=user,
            token="a" * 64,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        resp = self.client.get(reverse("verify-email", kwargs={"token": token.token}))
        self.assertRedirects(resp, reverse("profile"), fetch_redirect_response=False)
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
        self.assertFalse(EmailVerificationToken.objects.filter(user=user).exists())

    def test_verify_expired_token_rejected(self):
        user = make_user(username="old")
        token = EmailVerificationToken.objects.create(
            user=user,
            token="b" * 64,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = self.client.get(reverse("verify-email", kwargs={"token": token.token}))
        self.assertRedirects(resp, reverse("campaign-list"))
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.email_verified)

    def test_verify_unknown_token_rejected(self):
        resp = self.client.get(reverse("verify-email", kwargs={"token": "nope"}))
        self.assertRedirects(resp, reverse("campaign-list"))
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_verification_sends_new_email(self):
        user = make_user(username="resendme")
        user.email = "resendme@example.com"
        user.save()
        self.client.force_login(user)
        resp = self.client.post(reverse("resend-verification"))
        self.assertRedirects(resp, reverse("profile"))
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_skips_when_already_verified(self):
        user = make_user(username="done")
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])
        self.client.force_login(user)
        self.client.post(reverse("resend-verification"))
        self.assertEqual(len(mail.outbox), 0)


class SavedCampaignTests(TestCase):
    def setUp(self):
        self.alice = make_user(username="alice")
        self.campaign = make_campaign(creator=make_user(username="creator"))

    def test_toggle_saves_then_unsaves(self):
        self.client.force_login(self.alice)
        url = reverse("campaign-toggle-saved", kwargs={"slug": self.campaign.slug})
        self.client.post(url)
        self.assertTrue(SavedCampaign.objects.filter(user=self.alice, campaign=self.campaign).exists())
        self.client.post(url)
        self.assertFalse(SavedCampaign.objects.filter(user=self.alice, campaign=self.campaign).exists())

    def test_saved_list_isolation(self):
        bob = make_user(username="bob")
        SavedCampaign.objects.create(user=self.alice, campaign=self.campaign)
        SavedCampaign.objects.create(
            user=bob, campaign=make_campaign(title="Bobs Thing", creator=bob)
        )
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("my-saved"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.campaign.title)
        self.assertNotContains(resp, "Bobs Thing")

    def test_anonymous_toggle_redirects_to_login(self):
        resp = self.client.post(
            reverse("campaign-toggle-saved", kwargs={"slug": self.campaign.slug})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)


class DonationExportTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from core.models import Donation

        self.alice = make_user(username="alice")
        self.campaign = make_campaign(creator=make_user(username="creator"))
        self.donation = Donation.objects.create(
            campaign=self.campaign,
            amount=Decimal("25.00"),
            donor=self.alice,
            message="Go team",
            transaction_id="SIM-abc123",
        )

    def test_export_requires_login(self):
        resp = self.client.get(reverse("donation-export"))
        self.assertEqual(resp.status_code, 302)

    def test_export_streams_csv_rows(self):
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("donation-export"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        content = resp.content.decode()
        rows = list(csv.reader(io.StringIO(content)))
        self.assertEqual(rows[0], ["donated_at", "campaign", "amount", "message", "transaction_id"])
        self.assertEqual(rows[1][1], self.campaign.title)
        self.assertEqual(rows[1][2], "25.00")
        self.assertIn("SIM-abc123", rows[1][4])


class PasswordResetTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_emails_user(self):
        user = User.objects.create_user(username="reset", email="reset@example.com", password="old-pass-123")
        resp = self.client.post(
            reverse("password_reset"), {"email": "reset@example.com"}
        )
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset@example.com", mail.outbox[0].to)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_full_reset_flow(self):
        user = User.objects.create_user(username="flow", email="flow@example.com", password="old-pass-123")
        self.client.post(reverse("password_reset"), {"email": "flow@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        start = body.find("/accounts/reset/")
        end = body.find("\n", start)
        token_url = body[start:end].strip()
        # First visit stores the token in the session and redirects to the
        # token-less set-password URL.
        resp = self.client.get(token_url)
        set_pw_url = resp.url
        resp = self.client.post(
            set_pw_url,
            {"new_password1": "brand-new-pass-456", "new_password2": "brand-new-pass-456"},
        )
        self.assertRedirects(resp, reverse("password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("brand-new-pass-456"))
