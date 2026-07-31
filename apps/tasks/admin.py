"""Administration Django des tâches."""

from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Présente les tâches avec des filtres de suivi opérationnel."""

    list_display = (
        "title",
        "owner",
        "project",
        "status",
        "priority",
        "planned_date",
        "deadline",
    )
    list_filter = ("status", "priority", "origin")
    search_fields = ("title", "description", "project__name", "owner__email")
