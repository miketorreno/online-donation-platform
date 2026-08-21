from django.urls import path

from .views import CampaignDetailView, DonateView, SignUpView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("campaigns/<slug:slug>/donate/", DonateView.as_view(), name="campaign-donate"),
    path("campaigns/<slug:slug>/", CampaignDetailView.as_view(), name="campaign-detail"),
]
