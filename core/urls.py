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
    CampaignStatsView,
    DonateView,
    MyCampaignsView,
    MyDonationsView,
    NotificationsView,
    ProfileUpdateView,
    ProfileView,
    SavedCampaignsView,
    SignUpView,
    VerifyEmailView,
)

urlpatterns = [
    path("", CampaignListView.as_view(), name="campaign-list"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("accounts/verify/resend/", views.resend_verification, name="resend-verification"),
    path("accounts/verify/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("my/campaigns/", MyCampaignsView.as_view(), name="my-campaigns"),
    path("my/donations/", MyDonationsView.as_view(), name="my-donations"),
    path("my/donations/export/", views.donation_export, name="donation-export"),
    path("my/saved/", SavedCampaignsView.as_view(), name="my-saved"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile-edit"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.mark_notification_read,
        name="notification-read",
    ),
    path(
        "notifications/read-all/",
        views.mark_all_notifications_read,
        name="notification-read-all",
    ),
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
    path(
        "campaigns/<slug:slug>/toggle-saved/",
        views.toggle_saved,
        name="campaign-toggle-saved",
    ),
    path(
        "campaigns/<slug:slug>/stats/export/",
        views.campaign_stats_export,
        name="campaign-stats-export",
    ),
    path(
        "campaigns/<slug:slug>/stats/",
        CampaignStatsView.as_view(),
        name="campaign-stats",
    ),
    path("campaigns/<slug:slug>/donate/", DonateView.as_view(), name="campaign-donate"),
    path("campaigns/<slug:slug>/", CampaignDetailView.as_view(), name="campaign-detail"),
]
