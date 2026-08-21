from django.contrib import admin

from .models import Campaign, Donation


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "category", "goal_amount", "current_amount", "end_date", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "amount", "campaign", "donor", "donated_at")
    list_filter = ("donated_at",)
    search_fields = ("transaction_id", "donor__username")
