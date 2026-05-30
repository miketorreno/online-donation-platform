from decimal import Decimal
from django.db import models
from django.conf import settings  # Recommended for referencing the User model
from django.core.validators import MinValueValidator
from django.utils import timezone


class Campaign(models.Model):
    """
    Represents a fundraising campaign created by a user.
    """

    title = models.CharField(
        max_length=200, help_text="The title of the fundraising campaign."
    )
    description = models.TextField(
        help_text="A detailed description of the campaign's purpose."
    )
    goal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("10.00"))],
        help_text="The target fundraising amount in your currency (e.g., USD).",
    )
    current_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="The total amount raised so far.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="The date and time the campaign was created."
    )
    end_date = models.DateField(help_text="The date the campaign is scheduled to end.")
    is_active = models.BooleanField(
        default=True, help_text="Is the campaign currently accepting donations?"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Use settings.AUTH_USER_MODEL for flexibility
        on_delete=models.CASCADE,
        related_name="campaigns",
        help_text="The user who created this campaign.",
    )

    class Meta:
        ordering = ["-created_at"]  # Show newest campaigns first by default
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        """
        String representation of the Campaign model, used in the Django admin.
        """
        return self.title

    # === Helper Properties ===
    @property
    def percentage_raised(self):
        """
        Calculates the percentage of the goal amount that has been raised.
        """
        if self.goal_amount > 0:
            return min(round((self.current_amount / self.goal_amount) * 100, 2), 100)
        return 0

    @property
    def days_remaining(self):
        """
        Calculates the number of days left until the campaign ends.
        """

        today = timezone.now().date()
        if self.end_date >= today:
            return (self.end_date - today).days
        return 0


class Donation(models.Model):
    """
    Represents a single donation made to a campaign by a user or an anonymous donor.
    """

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],  # Enforce a minimum donation
        help_text="The amount of the donation.",
    )
    # This ID comes from the payment processor (e.g., Stripe's charge ID)
    # It's crucial for tracking and refunds.
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="The transaction ID from the payment gateway.",
    )
    donated_at = models.DateTimeField(
        auto_now_add=True, help_text="The date and time the donation was made."
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,  # If a campaign is deleted, its donation records are also deleted.
        related_name="donations",
        help_text="The campaign this donation is for.",
    )
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # If a donor deletes their account, we keep the donation record but unlink the donor.
        null=True,  # Allows for anonymous donations where no user is logged in.
        blank=True,  # Allows the field to be empty in forms.
        related_name="donations",
        help_text="The user who made the donation. Can be empty for anonymous donations.",
    )

    class Meta:
        ordering = ["-donated_at"]  # Show most recent donations first
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def __str__(self):
        """
        String representation of the Donation model.
        """
        donor_name = self.donor.username if self.donor else "Anonymous"
        return f"{donor_name} donated {self.amount} to {self.campaign.title}"
