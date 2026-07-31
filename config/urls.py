"""Routage HTTP principal de Project Pilot."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("compte/", include("apps.accounts.urls")),
    path("projets/", include("apps.projects.urls")),
    path("taches/", include("apps.tasks.urls")),
    path("boite-reception/", include("apps.inbox.urls")),
    path("reunions/", include("apps.meetings.urls")),
    path("calendrier/", include("apps.calendarapp.urls")),
    path("", include("apps.dashboard.urls")),
]
