from django.db.models import Count
from rest_framework import serializers

from core.models import Campaign, CampaignUpdate, Donation


class CampaignUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignUpdate
        fields = ["id", "title", "body", "image", "is_pinned", "created_at"]


class DonationSerializer(serializers.ModelSerializer):
    donor_username = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = ["amount", "donor_username", "message", "donated_at"]

    def get_donor_username(self, obj) -> str | None:
        return obj.donor.username if obj.donor else None


class CampaignSerializer(serializers.ModelSerializer):
    percentage_raised = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    supporter_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "title",
            "slug",
            "description",
            "goal_amount",
            "current_amount",
            "end_date",
            "is_active",
            "category",
            "cover_image",
            "percentage_raised",
            "days_remaining",
            "supporter_count",
        ]

    def get_percentage_raised(self, obj) -> float:
        return obj.percentage_raised

    def get_days_remaining(self, obj) -> int:
        return obj.days_remaining

    def get_supporter_count(self, obj) -> int:
        if hasattr(obj, "supporter_count"):
            return obj.supporter_count
        return obj.donations.aggregate(c=Count("id", distinct=True))["c"]


class CampaignListSerializer(CampaignSerializer):
    supporter_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "title",
            "slug",
            "goal_amount",
            "current_amount",
            "end_date",
            "category",
            "percentage_raised",
            "days_remaining",
            "supporter_count",
        ]


class CampaignWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ["title", "description", "goal_amount", "end_date", "category", "cover_image"]
