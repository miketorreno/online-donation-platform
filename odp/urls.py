from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.forms import StyledAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=StyledAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            subject_template_name="registration/password_reset_subject.txt",
            email_template_name="registration/password_reset_email.html",
            success_url="/accounts/password_reset/done/",
            html_email_template_name=None,
        ),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/v1/", include("core.api.urls")),
    path("", include("core.urls")),
]
