"""Configuration de l'application transverse."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Déclare les fonctionnalités communes du projet."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Commun"
