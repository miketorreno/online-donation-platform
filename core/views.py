from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, FormView

from .forms import DonateForm, StyledUserCreationForm
from .models import Campaign
from .services import DonationError, record_donation


class SignUpView(CreateView):
    form_class = StyledUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "core/signup.html"


class CampaignDetailView(DetailView):
    model = Campaign
    context_object_name = "campaign"
    template_name = "core/campaign_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.object
        ctx["recent_donations"] = campaign.donations.select_related("donor")[:10]
        ctx["supporter_count"] = campaign.donations.count()
        ctx["can_receive"] = campaign.is_active and campaign.days_remaining > 0
        return ctx


class DonateView(FormView):
    form_class = DonateForm
    template_name = "core/donate.html"

    def dispatch(self, request, *args, **kwargs):
        self.campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["campaign"] = self.campaign
        return ctx

    def _not_accepting(self):
        messages.error(self.request, "This campaign is not accepting donations.")
        return redirect("campaign-detail", slug=self.campaign.slug)

    def get(self, request, *args, **kwargs):
        if not (self.campaign.is_active and self.campaign.days_remaining > 0):
            return self._not_accepting()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not (self.campaign.is_active and self.campaign.days_remaining > 0):
            return self._not_accepting()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        donor = self.request.user if self.request.user.is_authenticated else None
        try:
            record_donation(
                campaign=self.campaign,
                amount=form.cleaned_data["amount"],
                donor=donor,
                message=form.cleaned_data.get("message", ""),
            )
        except DonationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        amount = form.cleaned_data["amount"]
        messages.success(self.request, f'Thank you! Your ${amount:,.2f} gift to "{self.campaign.title}" is confirmed.')
        return redirect("campaign-detail", slug=self.campaign.slug)
