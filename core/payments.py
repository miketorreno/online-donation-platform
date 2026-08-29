"""Payment provider abstraction.

A `PaymentProvider` is responsible for turning an amount into a confirmed
`transaction_id`. The default `SimulatedProvider` issues ids with the `SIM-`
prefix (matching historical behavior); a real gateway (e.g. Stripe) implements
the same protocol and returns the gateway's id.

Selection is driven by the `PAYMENT_PROVIDER` setting (default "simulated").
"""
import uuid
from decimal import Decimal

from django.conf import settings


def generate_simulated_transaction_id() -> str:
    """Simulated gateway id. Preserve the `SIM-` prefix for future migration."""
    return "SIM-" + uuid.uuid4().hex


class PaymentProvider:
    """Minimal interface a real gateway adapter must satisfy."""

    def charge(self, *, amount: Decimal, donor=None, campaign=None) -> str:
        """Return a transaction id for a successful charge, or raise."""
        raise NotImplementedError


class SimulatedProvider(PaymentProvider):
    """No-op provider that issues a deterministic-prefix id; no money moves."""

    def charge(self, *, amount, donor=None, campaign=None) -> str:
        return generate_simulated_transaction_id()


def get_provider() -> PaymentProvider:
    """Return the configured payment provider instance."""
    name = getattr(settings, "PAYMENT_PROVIDER", "simulated")
    if name == "simulated":
        return SimulatedProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER: {name!r}")
