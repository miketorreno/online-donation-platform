from django.db.models import Avg, Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from core.models import Campaign, CampaignUpdate, Donation

from .serializers import (
    CampaignListSerializer,
    CampaignSerializer,
    CampaignUpdateSerializer,
    CampaignWriteSerializer,
    DonationSerializer,
)


class ReadOnlyOrOwner(permissions.BasePermission):
    """Allow anonymous read; writes require a token + the campaign owner."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        campaign = getattr(view, "campaign", obj)
        return campaign.creator_id == request.user.id


class CampaignListView(generics.ListAPIView):
    serializer_class = CampaignListSerializer

    def get_queryset(self):
        qs = Campaign.objects.filter(is_active=True).annotate(
            supporter_count=Count("donations", distinct=True)
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        category = self.request.query_params.get("category", "")
        if category in Campaign.Category.values:
            qs = qs.filter(category=category)
        sort = self.request.query_params.get("sort", "newest")
        sorts = {
            "newest": "-created_at",
            "funded": "-current_amount",
            "closing": "end_date",
        }
        return qs.order_by(sorts.get(sort, "-created_at"))


class CampaignRetrieveView(generics.RetrieveAPIView):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"


class CampaignUpdateListView(generics.ListAPIView):
    serializer_class = CampaignUpdateSerializer

    def get_queryset(self):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        self.campaign = campaign
        return campaign.updates.all()


class CampaignDonationListView(generics.ListAPIView):
    serializer_class = DonationSerializer

    def get_queryset(self):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        self.campaign = campaign
        return campaign.donations.select_related("donor").order_by("-donated_at")[:50]


class CampaignUpdateCreateView(generics.CreateAPIView):
    serializer_class = CampaignUpdateSerializer
    permission_classes = [ReadOnlyOrOwner]

    def perform_create(self, serializer):
        campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        if campaign.creator_id != self.request.user.id:
            raise PermissionDenied
        serializer.save(campaign=campaign)


class CampaignCreateView(generics.CreateAPIView):
    serializer_class = CampaignWriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class CampaignOwnedUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampaignWriteSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrOwner]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return Campaign.objects.filter(creator=self.request.user)


class CampaignStatsView(generics.RetrieveAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrOwner]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return Campaign.objects.filter(creator=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        donations = instance.donations
        totals = donations.aggregate(
            total=Coalesce(Sum("amount"), Value(Decimal("0.00"))),
            average=Coalesce(Avg("amount"), Value(Decimal("0.00"))),
            maximum=Coalesce(Max("amount"), Value(Decimal("0.00"))),
            count=Count("id"),
            supporters=Count("donor", distinct=True),
        )
        from rest_framework.response import Response

        return Response(
            {
                "title": instance.title,
                "slug": instance.slug,
                "total_raised": totals["total"],
                "average_donation": totals["average"],
                "maximum_donation": totals["maximum"],
                "donation_count": totals["count"],
                "supporter_count": totals["supporters"],
            }
        )
