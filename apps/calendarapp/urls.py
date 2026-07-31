"""Routes du calendrier et de son flux JSON."""

from django.urls import path

from . import views

app_name = "calendar"

urlpatterns = [
    path("", views.calendar_view, name="view"),
    path("evenements/", views.calendar_events, name="events"),
    path(
        "taches/<uuid:task_id>/planifier/",
        views.reschedule_calendar_task,
        name="reschedule_task",
    ),
]
