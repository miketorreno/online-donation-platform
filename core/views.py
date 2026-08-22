from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .forms import CampaignForm, DonateForm, StyledUserCreationForm
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


SORTS = {"newest": "-created_at", "funded": "-current_amount", "closing": "end_date"}


class CampaignListView(ListView):
    model = Campaign
    paginate_by = 9
    context_object_name = "campaigns"
    template_name = "core/home.html"

    def get_queryset(self):
        qs = Campaign.objects.filter(is_active=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        category = self.request.GET.get("category", "")
        if category in Campaign.Category.values:
            qs = qs.filter(category=category)
        sort = self.request.GET.get("sort", "newest")
        return qs.annotate(
            supporter_count=Count("donations", distinct=True)
        ).order_by(SORTS.get(sort, SORTS["newest"]))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            q=self.request.GET.get("q", ""),
            active_category=self.request.GET.get("category", ""),
            active_sort=self.request.GET.get("sort", "newest"),
            categories=Campaign.Category.choices,
        )
        return ctx


class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "core/campaign_form.html"

    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Campaign created.")
        return response


class CampaignUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "core/campaign_form.html"

    def test_func(self):
        return self.get_object().creator_id == self.request.user.id

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Campaign updated.")
        return response


class CampaignDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Campaign
    template_name = "core/campaign_confirm_delete.html"
    success_url = reverse_lazy("my-campaigns")

    def test_func(self):
        return self.get_object().creator_id == self.request.user.id

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied

    def form_valid(self, form):
        messages.success(self.request, "Campaign deleted.")
        return super().form_valid(form)


@require_POST
@login_required
def toggle_active(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    if campaign.creator_id != request.user.id:
        raise PermissionDenied
    campaign.is_active = not campaign.is_active
    campaign.save(update_fields=["is_active"])
    if campaign.is_active:
        messages.success(request, "Campaign resumed.")
    else:
        messages.success(request, "Campaign paused.")
    return redirect("campaign-detail", slug=campaign.slug)


class MyCampaignsView(LoginRequiredMixin, ListView):
    model = Campaign
    context_object_name = "campaigns"
    template_name = "core/my_campaigns.html"

    def get_queryset(self):
        return (
            Campaign.objects.filter(creator=self.request.user)
            .annotate(
                raised=Coalesce(Sum("donations__amount"), Value(Decimal("0.00"))),
                supporter_count=Count("donations", distinct=True),
            )
            .order_by("-created_at")
        )


class MyDonationsView(LoginRequiredMixin, ListView):
    context_object_name = "donations"
    template_name = "core/my_donations.html"

    def get_queryset(self):
        return self.request.user.donations.select_related("campaign")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        total = self.object_list.aggregate(total=Sum("amount"))["total"]
        ctx["total_given"] = total or Decimal("0.00")
        return ctx
