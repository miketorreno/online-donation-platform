from django.contrib import admin

from .models import Campaign, CampaignUpdate, Donation


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
