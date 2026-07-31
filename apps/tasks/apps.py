"""Configuration de l'application des tâches."""

from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Déclare le domaine de gestion des tâches."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
    verbose_name = "Tâches"
