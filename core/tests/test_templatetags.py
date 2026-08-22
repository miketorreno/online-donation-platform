import hashlib
from decimal import Decimal

from django.test import TestCase

from core.models import Campaign
from core.templatetags.odp_extras import GRADIENTS, cover_art, usd
from core.tests.test_models import make_campaign


class CoverArtTests(TestCase):
    def test_returns_inline_gradient_style(self):
        c = make_campaign(slug="abc")
        self.assertTrue(cover_art(c).startswith("background-image:linear-gradient("))

    def test_same_slug_is_deterministic(self):
        c = make_campaign(slug="abc")
        self.assertEqual(cover_art(c), cover_art(c))
        self.assertEqual(cover_art(Campaign(slug="abc")), cover_art(c))

    def test_known_slugs_map_to_expected_gradients(self):
        for slug in ["abc", "clean-water-wells"]:
            digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
            h = int(digest, 16)
            c1, c2 = GRADIENTS[h % len(GRADIENTS)]
            angle = 100 + (h // 7) % 80
            expected = f"background-image:linear-gradient({angle}deg,{c1},{c2})"
            self.assertEqual(cover_art(Campaign(slug=slug)), expected)


class UsdFilterTests(TestCase):
    def test_formats_decimal_with_thousands_separator(self):
        self.assertEqual(usd(Decimal("1234.5")), "$1,234.50")

    def test_non_numeric_value_passes_through(self):
        self.assertEqual(usd("x"), "x")
