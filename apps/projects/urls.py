"""Routes de gestion des projets et macro-activités."""

from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("archives/", views.archived_project_list, name="archive_list"),
    path("nouveau/", views.project_create, name="create"),
    path("<uuid:project_id>/", views.project_detail, name="detail"),
    path("<uuid:project_id>/modifier/", views.project_update, name="update"),
    path("<uuid:project_id>/archiver/", views.project_archive, name="archive"),
    path("<uuid:project_id>/reactiver/", views.project_reactivate, name="reactivate"),
    path("<uuid:project_id>/supprimer/", views.project_delete, name="delete"),
    path(
        "<uuid:project_id>/activites/nouvelle/",
        views.macro_activity_create,
        name="activity_create",
    ),
    path(
        "activites/<uuid:activity_id>/modifier/",
        views.macro_activity_update,
        name="activity_update",
    ),
    path(
        "activites/<uuid:activity_id>/supprimer/",
        views.macro_activity_delete,
        name="activity_delete",
    ),
]
