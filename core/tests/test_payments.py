from decimal import Decimal

from django.test import SimpleTestCase
from django.test.utils import override_settings

from core.payments import SimulatedProvider, get_provider


class PaymentProviderTests(SimpleTestCase):
    def test_default_provider_is_simulated(self):
        self.assertIsInstance(get_provider(), SimulatedProvider)

    def test_simulated_id_has_sim_prefix(self):
        tx = SimulatedProvider().charge(amount=Decimal("10.00"))
        self.assertTrue(tx.startswith("SIM-"))

    @override_settings(PAYMENT_PROVIDER="unknown")
    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            get_provider()
