from decimal import Decimal
from django.db import models
from django.conf import settings  # Recommended for referencing the User model
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class BaseModel(models.Model):
    """Abstract base providing consistent created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Campaign(BaseModel):
    """
    Represents a fundraising campaign created by a user.
    """

    title = models.CharField(
        max_length=200, help_text="The title of the fundraising campaign."
    )
    slug = models.SlugField(
        unique=True,
        max_length=200,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from the title if left blank.",
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

    class Category(models.TextChoices):
        EMERGENCY = "emergency", "Emergency"
        MEDICAL = "medical", "Medical"
        EDUCATION = "education", "Education"
        ANIMALS = "animals", "Animals"
        ENVIRONMENT = "environment", "Environment"
        COMMUNITY = "community", "Community"
        SPORTS = "sports", "Sports"
        ARTS = "arts", "Arts"

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.COMMUNITY,
        help_text="The cause category this campaign belongs to.",
    )
    cover_image = models.ImageField(
        upload_to="covers/",
        blank=True,
        null=True,
        help_text="Optional upload; falls back to the generated gradient cover art.",
    )
    funded_notified = models.BooleanField(
        default=False,
        help_text="Whether the funded notification has already been sent.",
    )
    expiring_notified = models.BooleanField(
        default=False,
        help_text="Whether the expiring-soon notification has already been sent.",
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

    def get_absolute_url(self):
        return reverse("campaign-detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        max_length = self._meta.get_field("slug").max_length
        base = slugify(self.title) or "campaign"
        slug = base[:max_length]
        index = 2
        while Campaign.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            suffix = f"-{index}"
            slug = base[: max_length - len(suffix)] + suffix
            index += 1
        return slug

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
    message = models.TextField(
        blank=True,
        help_text="An optional message from the donor.",
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


class CampaignUpdate(BaseModel):
    """
    A public update/milestone posted by a campaign's creator (updates timeline).
    """

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="updates",
        help_text="The campaign this update belongs to.",
    )
    title = models.CharField(
        max_length=200, help_text="Short headline for the update."
    )
    body = models.TextField(
        help_text="The full text of the update."
    )
    image = models.ImageField(
        upload_to="updates/",
        blank=True,
        null=True,
        help_text="Optional image to accompany the update.",
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin this update to the top of the campaign timeline.",
    )

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        verbose_name = "Campaign Update"
        verbose_name_plural = "Campaign Updates"

    def __str__(self):
        return f"{self.title} ({self.campaign.title})"


class Profile(BaseModel):
    """
    Extended identity fields for a user (created alongside the user).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="The user this profile belongs to.",
    )
    display_name = models.CharField(
        max_length=100, blank=True, help_text="Name to show instead of the username."
    )
    bio = models.TextField(
        blank=True, help_text="A short bio shown on the profile."
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="Optional profile picture.",
    )
    timezone = models.CharField(
        max_length=64, default="UTC", help_text="The user's timezone."
    )
    email_verified = models.BooleanField(
        default=False, help_text="Whether the email address has been verified."
    )
    receives_email_updates = models.BooleanField(
        default=True, help_text="Opt in to email updates for saved campaigns."
    )

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return self.display_name or self.user.username


class EmailVerificationToken(BaseModel):
    """
    Single-use token for verifying a user's email address.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_token",
        help_text="The user this verification token belongs to.",
    )
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(
        help_text="When the token stops being valid."
    )

    class Meta:
        verbose_name = "Email Verification Token"
        verbose_name_plural = "Email Verification Tokens"

    def __str__(self):
        return f"{self.user} ({self.token[:8]}...)"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class SavedCampaign(BaseModel):
    """
    A campaign a user wants to follow (receives update notifications by default).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_campaigns",
        help_text="The user who saved this campaign.",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="saved_by",
        help_text="The saved campaign.",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "campaign"], name="unique_user_campaign_save"
            )
        ]
        verbose_name = "Saved Campaign"
        verbose_name_plural = "Saved Campaigns"

    def __str__(self):
        return f"{self.user} saved {self.campaign.title}"


class Notification(BaseModel):
    """
    An in-app notification delivered to a recipient (informational only).
    """

    class Kind(models.TextChoices):
        UPDATE_POSTED = "update_posted", "Update posted"
        CAMPAIGN_FUNDED = "campaign_funded", "Campaign funded"
        EXPIRING_SOON = "expiring_soon", "Expiring soon"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="The user who receives this notification.",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        help_text="The type of notification.",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="The related campaign, if any.",
    )
    update = models.ForeignKey(
        CampaignUpdate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="The related campaign update, if any.",
    )
    message = models.CharField(
        max_length=300,
        help_text="Human-readable notification text.",
    )
    read = models.BooleanField(default=False, help_text="Whether the user has read it.")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.recipient}: {self.message}"

