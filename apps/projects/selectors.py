"""Sélecteurs centralisant la lecture sécurisée des projets."""

from django.db.models import QuerySet

from apps.accounts.models import User

from .models import MacroActivity, Project


def get_projects_for_user(
    *, user: User, include_archived: bool = False
) -> QuerySet[Project]:
    """Retourne les projets appartenant à un utilisateur.

    Les projets archivés sont exclus par défaut des vues opérationnelles.
    """
    projects = Project.objects.filter(owner=user)
    if not include_archived:
        projects = projects.exclude(status=Project.Status.ARCHIVED)
    return projects


def get_macro_activities_for_user(*, user: User) -> QuerySet[MacroActivity]:
    """Retourne les macro-activités accessibles à un utilisateur."""
    return MacroActivity.objects.filter(project__owner=user).select_related("project")
