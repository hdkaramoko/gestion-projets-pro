"""Administration des réunions et actions associées."""

from django.contrib import admin

from .models import Meeting, MeetingAction


class MeetingActionInline(admin.TabularInline):
    """Permet de consulter les actions dans la fiche de réunion."""

    model = MeetingAction
    extra = 0
    readonly_fields = ("created_task",)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    """Facilite la recherche des comptes rendus."""

    list_display = ("title", "project", "owner", "scheduled_at")
    list_filter = ("scheduled_at",)
    search_fields = ("title", "participants", "project__name", "owner__email")
    inlines = (MeetingActionInline,)


@admin.register(MeetingAction)
class MeetingActionAdmin(admin.ModelAdmin):
    """Présente les actions et leur état de conversion."""

    list_display = ("title", "meeting", "assignee", "deadline", "created_task")
    list_filter = ("priority",)
    search_fields = ("title", "meeting__title", "assignee")
    readonly_fields = ("created_task",)
