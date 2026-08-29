from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    CampaignForm,
    CampaignUpdateForm,
    DonateForm,
    ProfileForm,
    StyledUserCreationForm,
)
from .models import (
    Campaign,
    CampaignUpdate,
    EmailVerificationToken,
    Profile,
    SavedCampaign,
)
from .services import DonationError, record_donation


class SignUpView(CreateView):
    form_class = StyledUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "core/signup.html"

    def form_valid(self, form):
        from .emails import send_verification_email

        response = super().form_valid(form)
        user = self.object
        if user.email:
            send_verification_email(user)
        return response


class CampaignDetailView(DetailView):
    model = Campaign
    context_object_name = "campaign"
    template_name = "core/campaign_detail.html"
    updates_limit = 50

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.object
        ctx["recent_donations"] = campaign.donations.select_related("donor")[:10]
        ctx["supporter_count"] = campaign.donations.count()
        ctx["can_receive"] = campaign.is_active and campaign.days_remaining > 0
        ctx["updates"] = campaign.updates.all()[: self.updates_limit]
        ctx["is_owner"] = (
            hasattr(self.request, "user") and self.request.user.is_authenticated
            and campaign.creator_id == self.request.user.id
        )
        if self.request.user.is_authenticated:
            ctx["is_saved"] = SavedCampaign.objects.filter(
                user=self.request.user, campaign=campaign
            ).exists()
        else:
            ctx["is_saved"] = False
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


class OwnerOrDeniedMixin(UserPassesTestMixin):
    """Require the requesting user to own the targeted campaign."""

    def get_campaign(self):
        if not hasattr(self, "campaign"):
            self.campaign = None
        return self.campaign

    def test_func(self):
        campaign = self.get_campaign()
        if campaign is None:
            return False
        return campaign.creator_id == self.request.user.id

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied


class CampaignUpdateCreateView(LoginRequiredMixin, OwnerOrDeniedMixin, CreateView):
    model = CampaignUpdate
    form_class = CampaignUpdateForm
    template_name = "core/campaignupdate_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_campaign(self):
        return self.campaign

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["campaign"] = self.campaign
        return ctx

    def form_valid(self, form):
        form.instance.campaign = self.campaign
        response = super().form_valid(form)
        messages.success(self.request, "Update posted.")
        return response

    def get_success_url(self):
        return reverse("campaign-detail", kwargs={"slug": self.campaign.slug})


class CampaignUpdateUpdateView(LoginRequiredMixin, OwnerOrDeniedMixin, UpdateView):
    model = CampaignUpdate
    form_class = CampaignUpdateForm
    template_name = "core/campaignupdate_form.html"

    def get_campaign(self):
        return self.get_object().campaign

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["campaign"] = self.get_object().campaign
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Update saved.")
        return response

    def get_success_url(self):
        return reverse("campaign-detail", kwargs={"slug": self.get_object().campaign.slug})


class CampaignUpdateDeleteView(LoginRequiredMixin, OwnerOrDeniedMixin, DeleteView):
    model = CampaignUpdate
    template_name = "core/campaignupdate_confirm_delete.html"

    def get_campaign(self):
        return self.get_object().campaign

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["campaign"] = self.get_object().campaign
        return ctx

    def form_valid(self, form):
        campaign = self.get_object().campaign
        response = super().form_valid(form)
        messages.success(self.request, "Update deleted.")
        self._success_campaign_slug = campaign.slug
        return response

    def get_success_url(self):
        slug = getattr(self, "_success_campaign_slug", None)
        if slug is None:
            slug = self.get_object().campaign.slug
        return reverse("campaign-detail", kwargs={"slug": slug})


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


@login_required
def donation_export(request):
    import csv

    from django.utils import timezone

    donations = (
        request.user.donations.select_related("campaign")
        .order_by("-donated_at")
    )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="donations-{timezone.now().strftime("%Y%m%d")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["donated_at", "campaign", "amount", "message", "transaction_id"])
    for d in donations:
        writer.writerow(
            [
                d.donated_at.isoformat(),
                d.campaign.title,
                str(d.amount),
                d.message,
                d.transaction_id or "",
            ]
        )
    return response


class ProfileView(LoginRequiredMixin, DetailView):
    model = Profile
    context_object_name = "profile"
    template_name = "core/profile.html"

    def get_object(self, queryset=None):
        return Profile.objects.get_or_create(user=self.request.user)[0]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_owner"] = True
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "core/profile_form.html"

    def get_object(self, queryset=None):
        return Profile.objects.get_or_create(user=self.request.user)[0]

    def get_success_url(self):
        return reverse("profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Profile updated.")
        return response


class VerifyEmailView(DetailView):
    model = EmailVerificationToken
    slug_field = "token"
    slug_url_kwarg = "token"
    template_name = "core/verify_email.html"

    def get_object(self, queryset=None):
        season = EmailVerificationToken.objects.filter(
            token=self.kwargs.get("token")
        ).select_related("user").first()
        if season is None:
            return None
        return season

    def get(self, request, *args, **kwargs):
        token = self.get_object()
        if token is None or token.is_expired:
            messages.error(request, "This verification link is invalid or has expired.")
            return redirect("campaign-list")
        profile = Profile.objects.get_or_create(user=token.user)[0]
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])
        token.delete()
        messages.success(request, "Your email has been verified.")
        return redirect("profile")


@login_required
def resend_verification(request):
    from .emails import send_verification_email

    profile = Profile.objects.get_or_create(user=request.user)[0]
    if profile.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        send_verification_email(request.user)
        messages.success(request, "A new verification email has been sent.")
    return redirect("profile")


@require_POST
@login_required
def toggle_saved(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    saved, created = SavedCampaign.objects.get_or_create(
        user=request.user, campaign=campaign
    )
    if created:
        messages.success(request, f"Saved \"{campaign.title}\".")
    else:
        saved.delete()
        messages.info(request, f"Unsaved \"{campaign.title}\".")
    return redirect("campaign-detail", slug=campaign.slug)


class SavedCampaignsView(LoginRequiredMixin, ListView):
    context_object_name = "campaigns"
    template_name = "core/my_saved.html"

    def get_queryset(self):
        return (
            Campaign.objects.filter(saved_by__user=self.request.user)
            .distinct()
            .order_by("-saved_by__created_at")
        )


class NotificationsView(LoginRequiredMixin, ListView):
    context_object_name = "notifications"
    template_name = "core/notifications.html"
    paginate_by = 20

    def get_queryset(self):
        return (
            self.request.user.notifications.select_related("campaign").order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["unread_count"] = self.request.user.notifications.filter(read=False).count()
        return ctx


@require_POST
@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        request.user.notifications, pk=pk
    )
    notification.read = True
    notification.save(update_fields=["read"])
    return redirect("notifications")


@require_POST
@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(read=False).update(read=True)
    return redirect("notifications")


class CampaignStatsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/stats.html"

    def dispatch(self, request, *args, **kwargs):
        self.campaign = get_object_or_404(Campaign, slug=self.kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.campaign.creator_id == self.request.user.id

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.campaign
        donations = campaign.donations

        totals = donations.aggregate(
            total=Coalesce(Sum("amount"), Value(Decimal("0.00"))),
            average=Coalesce(Avg("amount"), Value(Decimal("0.00"))),
            maximum=Coalesce(Max("amount"), Value(Decimal("0.00"))),
            count=Count("id"),
            supporter_count=Count("donor", distinct=True),
        )
        with_message = donations.filter(message__iregex=r"\w").count()

        daily = (
            donations.annotate(day=TruncDate("donated_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        running = Decimal("0.00")
        trend = []
        for entry in daily:
            running += entry["total"]
            trend.append(
                {
                    "day": entry["day"],
                    "daily": entry["total"],
                    "cumulative": running,
                }
            )
        trend.reverse()

        top_supporters = (
            donations.exclude(donor=None)
            .values("donor__username")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")[:10]
        )

        ctx.update(
            campaign=campaign,
            total_raised=totals["total"],
            average_donation=totals["average"],
            maximum_donation=totals["maximum"],
            donation_count=totals["count"],
            supporter_count=totals["supporter_count"],
            with_message_count=with_message,
            without_message_count=totals["count"] - with_message,
            trend=trend,
            top_supporters=top_supporters,
        )
        return ctx


@login_required
def campaign_stats_export(request, slug):
    import csv

    from django.utils import timezone

    campaign = get_object_or_404(Campaign, slug=slug)
    if campaign.creator_id != request.user.id:
        raise PermissionDenied
    donations = campaign.donations.select_related("donor").order_by("-donated_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{campaign.slug}-donations-{timezone.now().strftime("%Y%m%d")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["donated_at", "donor", "amount", "message", "transaction_id"])
    for d in donations:
        writer.writerow(
            [
                d.donated_at.isoformat(),
                d.donor.username if d.donor else "Anonymous",
                str(d.amount),
                d.message,
                d.transaction_id or "",
            ]
        )
    return response
