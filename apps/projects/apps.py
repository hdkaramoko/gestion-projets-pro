"""Configuration de l'application des projets."""

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Déclare le domaine des projets et macro-activités."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    verbose_name = "Projets"
