"""Configuration de l'application du tableau de bord."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Déclare le tableau de bord et ses indicateurs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Tableau de bord"
