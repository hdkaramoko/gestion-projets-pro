"""Administration des projets et macro-activités."""

from django.contrib import admin

from .models import MacroActivity, Project


class MacroActivityInline(admin.TabularInline):
    """Affiche les macro-activités directement dans la fiche projet."""

    model = MacroActivity
    extra = 0
    fields = ("title", "status", "priority", "deadline", "display_order")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Facilite la recherche et le suivi des projets dans l'administration."""

    list_display = ("name", "owner", "status", "priority", "deadline")
    list_filter = ("status", "priority")
    search_fields = ("name", "owner__email")
    inlines = (MacroActivityInline,)


@admin.register(MacroActivity)
class MacroActivityAdmin(admin.ModelAdmin):
    """Présente les macro-activités avec leurs informations principales."""

    list_display = ("title", "project", "status", "priority", "deadline")
    list_filter = ("status", "priority")
    search_fields = ("title", "project__name", "project__owner__email")
