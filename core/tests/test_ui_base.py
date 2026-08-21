from django.test import TestCase


class BaseUITests(TestCase):
    def test_login_page_uses_new_shell(self):
        resp = self.client.get("/accounts/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "css/app.css")
        self.assertContains(resp, "fonts.googleapis.com")
        self.assertContains(resp, "skip-link")
        self.assertNotContains(resp, "bootstrap")

    def test_signup_page_renders_in_card(self):
        resp = self.client.get("/signup/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start your ODP account")
