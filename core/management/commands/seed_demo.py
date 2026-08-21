import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Campaign
from core.services import DonationError, record_donation

CAMPAIGNS = [
    # slug, title, category, goal, days_offset(end), donations_count
    ("rebuild-maple-street-community-garden", "Rebuild Maple Street Community Garden", "community", "5000.00", 45, 12),
    ("emergency-vet-care-for-rescue-puppies", "Emergency Vet Care for Rescue Puppies", "animals", "2500.00", 20, 9),
    ("laptops-for-linwood-middle-school", "Laptops for Linwood Middle School", "education", "8000.00", 60, 15),
    ("wildfire-relief-for-cedar-county", "Wildfire Relief for Cedar County", "emergency", "15000.00", 30, 34),
    ("riverside-trail-restoration", "Riverside Trail Restoration", "environment", "6000.00", -5, 11),
    ("youth-soccer-scholarships", "Youth Soccer Scholarships", "sports", "4000.00", 90, 5),
    ("community-mural-project", "Community Mural Project", "arts", "3000.00", 25, 8),
    ("free-dental-clinic-days", "Free Dental Clinic Days", "medical", "12000.00", 120, 19),
]

AMOUNTS = ["5.00", "10.00", "20.00", "25.00", "50.00", "75.00", "100.00", "250.00"]

MESSAGES = ["Happy to help!", "Great cause.", "", "", "For the kids.", "Keep going!", "", "In memory of Nan."]

DESCRIPTIONS = {
    "rebuild-maple-street-community-garden": (
        "Last winter's storms wrecked the raised beds at the Maple Street garden and half the "
        "plots have been unusable since. We're replacing the beds, repairing the shared water "
        "lines, and restocking tools so the forty families who garden here can plant this spring."
    ),
    "emergency-vet-care-for-rescue-puppies": (
        "Three litters of puppies arrived at our rescue last month, all needing parvo treatment "
        "and vaccinations before they can be adopted. This fund covers their vet bills while "
        "they finish recovery in foster homes."
    ),
    "laptops-for-linwood-middle-school": (
        "About a third of Linwood Middle School students have no working computer at home, even "
        "though homework now assumes one. We're buying durable Chromebooks and a charging cart "
        "so every student can borrow a laptop for the school year."
    ),
    "wildfire-relief-for-cedar-county": (
        "The Cedar County fires displaced more than two hundred households, many of which left "
        "with only what fit in the car. Donations go to immediate needs such as temporary "
        "housing, clothing, and food, coordinated through the county relief center."
    ),
    "riverside-trail-restoration": (
        "Spring flooding washed out two footbridges and a stretch of the Riverside Trail. We're "
        "rebuilding the crossings and regrading the path so the trail can safely reopen for the "
        "fall season."
    ),
    "youth-soccer-scholarships": (
        "Registration fees keep some kids in our rec league on the sidelines every season. "
        "Scholarships cover fees plus cleats and kit for players whose families cannot afford "
        "the cost."
    ),
    "community-mural-project": (
        "The east wall of the community center has been blank since the old sign came down. "
        "Local artists will design and paint a mural over three weekends with help from "
        "neighborhood volunteers."
    ),
    "free-dental-clinic-days": (
        "Our clinic runs quarterly free dental days for uninsured neighbors, but supplies for "
        "each event cost more than we have on hand. Donations cover sterilization, x-rays, "
        "fillings, and extractions for each clinic day."
    ),
}


class Command(BaseCommand):
    help = "Seed deterministic demo campaigns and donations owned by the 'demo' user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete the demo user's existing campaigns first, then reseed.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com"},
        )
        if created:
            user.set_password("demo-pass-1234")
            user.save()

        if options["force"]:
            deleted, _ = Campaign.objects.filter(creator=user).delete()
            self.stdout.write(f"Removed {deleted} existing demo campaigns.")

        rng = random.Random(42)
        today = timezone.now().date()
        created_count = 0
        total_donations = 0

        for slug, title, category, goal, days_offset, donations_count in CAMPAIGNS:
            campaign, was_created = Campaign.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": DESCRIPTIONS[slug],
                    "category": category,
                    "goal_amount": Decimal(goal),
                    "end_date": today + timedelta(days=days_offset),
                    "creator": user,
                },
            )
            inserted = 0
            if was_created:
                created_count += 1
                for i in range(donations_count):
                    amount = Decimal(rng.choice(AMOUNTS))
                    message = rng.choice(MESSAGES)
                    donor = user if i % 2 == 1 else None
                    try:
                        record_donation(campaign=campaign, amount=amount, donor=donor, message=message)
                        inserted += 1
                    except DonationError:
                        continue

            campaign.refresh_from_db(fields=["current_amount"])
            n = campaign.donations.count()
            total_donations += n
            self.stdout.write(self.style.SUCCESS(
                f"{campaign.slug}: ${campaign.current_amount} of ${campaign.goal_amount} ({n} donations)"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_count} new campaign(s); {total_donations} donations on file."
        ))
