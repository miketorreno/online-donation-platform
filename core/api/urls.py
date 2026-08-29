from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

from . import views

app_name = "api"

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="auth-token"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="api:schema"),
        name="swagger-ui",
    ),
    # campaign-create MUST precede the <slug> routes
    path("campaigns/", views.CampaignListView.as_view(), name="campaign-list"),
    path("campaigns/new/", views.CampaignCreateView.as_view(), name="campaign-create"),
    path(
        "campaigns/<slug:slug>/updates/new/",
        views.CampaignUpdateCreateView.as_view(),
        name="campaign-update-create",
    ),
    path(
        "campaigns/<slug:slug>/updates/",
        views.CampaignUpdateListView.as_view(),
        name="campaign-updates",
    ),
    path(
        "campaigns/<slug:slug>/donations/",
        views.CampaignDonationListView.as_view(),
        name="campaign-donations",
    ),
    path(
        "campaigns/<slug:slug>/stats/",
        views.CampaignStatsView.as_view(),
        name="campaign-stats",
    ),
    path(
        "campaigns/<slug:slug>/edit/",
        views.CampaignOwnedUpdateView.as_view(),
        name="campaign-edit",
    ),
    path(
        "campaigns/<slug:slug>/",
        views.CampaignRetrieveView.as_view(),
        name="campaign-detail",
    ),
]
