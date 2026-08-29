"""Celery application for the ODP project."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "odp.settings")

app = Celery("odp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
