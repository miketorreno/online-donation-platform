import hashlib
from decimal import Decimal

from django import template

register = template.Library()

GRADIENTS = [
    ("oklch(42% 0.11 155)", "oklch(65% 0.13 170)"),
    ("oklch(38% 0.10 250)", "oklch(55% 0.14 230)"),
    ("oklch(40% 0.12 320)", "oklch(60% 0.15 340)"),
    ("oklch(45% 0.12 60)", "oklch(70% 0.14 80)"),
    ("oklch(35% 0.09 190)", "oklch(58% 0.11 205)"),
    ("oklch(42% 0.13 140)", "oklch(66% 0.14 120)"),
]


@register.simple_tag
def cover_art(campaign):
    digest = hashlib.sha256(campaign.slug.encode("utf-8")).hexdigest()
    h = int(digest, 16)
    c1, c2 = GRADIENTS[h % len(GRADIENTS)]
    angle = 100 + (h // 7) % 80
    return f"background-image:linear-gradient({angle}deg,{c1},{c2})"


@register.filter
def usd(value):
    try:
        return f"${Decimal(value):,.2f}"
    except Exception:
        return value
