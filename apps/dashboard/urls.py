"""Routes du tableau de bord."""

from django.urls import path

from .views import dashboard

urlpatterns = [path("", dashboard, name="home")]
