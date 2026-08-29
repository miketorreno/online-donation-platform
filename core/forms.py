from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from core.models import Campaign, CampaignUpdate, Profile


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")


class StyledUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email address",
        required=True,
        help_text="We'll send a verification link to this address.",
        widget=forms.EmailInput(attrs={"class": "field-input"}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")


class DonateForm(forms.Form):
    amount = forms.DecimalField(
        label="Amount (USD)",
        min_value=Decimal("1.00"),
        max_digits=10,
        decimal_places=2,
        initial=Decimal("25.00"),
        error_messages={"min_value": "Minimum donation is $1.00."},
        widget=forms.NumberInput(attrs={"class": "field-input", "min": "1.00", "step": "0.01"}),
    )
    message = forms.CharField(
        label="Message (optional)",
        required=False,
        max_length=280,
        widget=forms.Textarea(attrs={"class": "field-input", "rows": 3}),
    )


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["title", "description", "category", "goal_amount", "end_date", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input"}),
            "description": forms.Textarea(attrs={"class": "field-input", "rows": 6}),
            "category": forms.Select(attrs={"class": "field-input"}),
            "goal_amount": forms.NumberInput(
                attrs={"class": "field-input", "min": "10.00", "step": "0.01"}
            ),
            "end_date": forms.DateInput(attrs={"class": "field-input", "type": "date"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "field-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "aria-describedby", f"id_{name}-help id_{name}-error"
            )


class CampaignUpdateForm(forms.ModelForm):
    class Meta:
        model = CampaignUpdate
        fields = ["title", "body", "image", "is_pinned"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input"}),
            "body": forms.Textarea(attrs={"class": "field-input", "rows": 6}),
            "image": forms.ClearableFileInput(attrs={"class": "field-input"}),
            "is_pinned": forms.CheckboxInput(attrs={"class": "h-5 w-5 accent-pine-700"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "aria-describedby", f"id_{name}-help id_{name}-error"
            )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "bio", "avatar", "timezone", "receives_email_updates"]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "field-input"}),
            "bio": forms.Textarea(attrs={"class": "field-input", "rows": 4}),
            "avatar": forms.ClearableFileInput(attrs={"class": "field-input"}),
            "timezone": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "UTC"}
            ),
            "receives_email_updates": forms.CheckboxInput(
                attrs={"class": "h-5 w-5 accent-pine-700"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "aria-describedby", f"id_{name}-help id_{name}-error"
            )
