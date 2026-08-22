import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.models import Campaign, Donation


class DonationError(Exception):
    pass


def generate_transaction_id() -> str:
    return "SIM-" + uuid.uuid4().hex


def record_donation(*, campaign: Campaign, amount: Decimal, donor=None, message: str = "") -> Donation:
    if amount < Decimal("1.00"):
        raise DonationError("Minimum donation is $1.00.")
    if not campaign.is_active or campaign.end_date < timezone.now().date():
        raise DonationError("This campaign is not accepting donations.")
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    with transaction.atomic():
        donation = Donation.objects.create(
            campaign=campaign,
            amount=quantized,
            donor=donor,
            message=(message or "").strip(),
            transaction_id=generate_transaction_id(),
        )
        Campaign.objects.filter(pk=campaign.pk).update(
            current_amount=F("current_amount") + quantized
        )
        campaign.refresh_from_db(fields=["current_amount"])
    return donation
