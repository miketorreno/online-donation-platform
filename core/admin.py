from django.contrib import admin

from .models import (
    Campaign,
    CampaignUpdate,
    Donation,
    EmailVerificationToken,
    Notification,
    Profile,
    SavedCampaign,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "category", "goal_amount", "current_amount", "end_date", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    fields = (
        "title",
        "slug",
        "description",
        "category",
        "goal_amount",
        "end_date",
        "cover_image",
        "is_active",
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "amount", "campaign", "donor", "donated_at")
    list_filter = ("donated_at",)
    search_fields = ("transaction_id", "donor__username")


@admin.register(CampaignUpdate)
class CampaignUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "campaign", "is_pinned", "created_at")
    list_filter = ("is_pinned", "campaign")
    search_fields = ("title", "body")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "email_verified", "timezone")
    list_filter = ("email_verified", "receives_email_updates")
    search_fields = ("user__username", "display_name")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at")
    search_fields = ("user__username", "token")


@admin.register(SavedCampaign)
class SavedCampaignAdmin(admin.ModelAdmin):
    list_display = ("user", "campaign", "created_at")
    search_fields = ("user__username", "campaign__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "campaign", "read", "created_at")
    list_filter = ("kind", "read")
    search_fields = ("recipient__username", "message")
