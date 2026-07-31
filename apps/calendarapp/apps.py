"""Configuration de l'application calendrier."""

from django.apps import AppConfig


class CalendarAppConfig(AppConfig):
    """Déclare le calendrier et son flux d'événements."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.calendarapp"
    verbose_name = "Calendrier"
