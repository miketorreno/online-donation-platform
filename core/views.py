from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView
from .forms import StyledUserCreationForm
from .models import Campaign


class SignUpView(CreateView):
    form_class = StyledUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "core/signup.html"
