"""Routes des réunions, comptes rendus et actions."""

from django.urls import path

from . import views

app_name = "meetings"

urlpatterns = [
    path("", views.meeting_list, name="list"),
    path("nouvelle/", views.meeting_create, name="create"),
    path("<uuid:meeting_id>/", views.meeting_detail, name="detail"),
    path("<uuid:meeting_id>/imprimer/", views.meeting_print, name="print"),
    path("<uuid:meeting_id>/modifier/", views.meeting_update, name="update"),
    path("<uuid:meeting_id>/supprimer/", views.meeting_delete, name="delete"),
    path(
        "<uuid:meeting_id>/actions/nouvelle/",
        views.meeting_action_create,
        name="action_create",
    ),
    path(
        "actions/<uuid:action_id>/modifier/",
        views.meeting_action_update,
        name="action_update",
    ),
    path(
        "actions/<uuid:action_id>/supprimer/",
        views.meeting_action_delete,
        name="action_delete",
    ),
    path(
        "actions/<uuid:action_id>/transformer/",
        views.meeting_action_convert,
        name="action_convert",
    ),
]
