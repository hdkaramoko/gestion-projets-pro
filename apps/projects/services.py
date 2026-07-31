"""Services métier modifiant l'état des projets."""

from django.utils import timezone

from .models import Project


def archive_project(*, project: Project) -> Project:
    """Archive un projet et mémorise la date de cette transition."""
    project.status = Project.Status.ARCHIVED
    project.archived_at = timezone.now()
    project.save(update_fields=("status", "archived_at", "updated_at"))
    return project


def reactivate_project(*, project: Project) -> Project:
    """Réactive un projet archivé et efface sa date d'archivage."""
    project.status = Project.Status.ACTIVE
    project.archived_at = None
    project.save(update_fields=("status", "archived_at", "updated_at"))
    return project
