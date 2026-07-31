"""Administration des éléments de boîte de réception."""

from django.contrib import admin

from .models import InboxItem


@admin.register(InboxItem)
class InboxItemAdmin(admin.ModelAdmin):
    """Présente les captures avec leur état de traitement."""

    list_display = ("content", "owner", "status", "created_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("content", "owner__email")
    readonly_fields = ("created_at", "processed_at", "converted_task")
