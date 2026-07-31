"""Routes de la boîte de réception."""

from django.urls import path

from . import views

app_name = "inbox"

urlpatterns = [
    path("", views.inbox_list, name="list"),
    path("archives/", views.inbox_archive_list, name="archive_list"),
    path("<uuid:item_id>/qualifier/", views.inbox_convert, name="convert"),
    path("<uuid:item_id>/ignorer/", views.inbox_ignore, name="ignore"),
    path("<uuid:item_id>/archiver/", views.inbox_archive, name="archive"),
    path("<uuid:item_id>/supprimer/", views.inbox_delete, name="delete"),
]
