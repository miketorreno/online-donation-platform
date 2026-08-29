from django.urls import path

from . import views
from .views import (
    CampaignCreateView,
    CampaignDeleteView,
    CampaignDetailView,
    CampaignListView,
    CampaignUpdateCreateView,
    CampaignUpdateDeleteView,
    CampaignUpdateUpdateView,
    CampaignUpdateView,
    DonateView,
    MyCampaignsView,
    MyDonationsView,
    SignUpView,
)

urlpatterns = [
    path("", CampaignListView.as_view(), name="campaign-list"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("my/campaigns/", MyCampaignsView.as_view(), name="my-campaigns"),
    path("my/donations/", MyDonationsView.as_view(), name="my-donations"),
    # campaign-create MUST precede every campaigns/<slug:slug>/... route
    # so "new" is never captured as a slug.
    path("campaigns/new/", CampaignCreateView.as_view(), name="campaign-create"),
    # Campaign update routes (before <slug> detail so "updates" leaves aren't eaten).
    path(
        "campaigns/<slug:slug>/updates/new/",
        CampaignUpdateCreateView.as_view(),
        name="campaign-update-create",
    ),
    path(
        "campaigns/<slug:slug>/updates/<int:pk>/edit/",
        CampaignUpdateUpdateView.as_view(),
        name="campaign-update-edit",
    ),
    path(
        "campaigns/<slug:slug>/updates/<int:pk>/delete/",
        CampaignUpdateDeleteView.as_view(),
        name="campaign-update-delete",
    ),
    path("campaigns/<slug:slug>/edit/", CampaignUpdateView.as_view(), name="campaign-edit"),
    path("campaigns/<slug:slug>/delete/", CampaignDeleteView.as_view(), name="campaign-delete"),
    path(
        "campaigns/<slug:slug>/toggle-active/",
        views.toggle_active,
        name="campaign-toggle-active",
    ),
    path("campaigns/<slug:slug>/donate/", DonateView.as_view(), name="campaign-donate"),
    path("campaigns/<slug:slug>/", CampaignDetailView.as_view(), name="campaign-detail"),
]
