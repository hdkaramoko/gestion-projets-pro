"""Configuration de l'application des réunions."""

from django.apps import AppConfig


class MeetingsConfig(AppConfig):
    """Déclare le domaine des réunions et de leurs actions."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.meetings"
    verbose_name = "Réunions"
