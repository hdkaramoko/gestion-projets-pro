"""Routes de gestion des tâches et de leurs actions rapides."""

from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("nouvelle/", views.task_create, name="create"),
    path("<uuid:task_id>/", views.task_detail, name="detail"),
    path("<uuid:task_id>/modifier/", views.task_update, name="update"),
    path("<uuid:task_id>/supprimer/", views.task_delete, name="delete"),
    path(
        "<uuid:task_id>/statut/<str:status>/",
        views.task_status,
        name="status",
    ),
    path(
        "<uuid:task_id>/reporter/",
        views.task_reschedule,
        name="reschedule",
    ),
    path(
        "<uuid:task_id>/echeance/",
        views.task_deadline,
        name="deadline",
    ),
]
