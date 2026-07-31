"""Configuration de l'application de boîte de réception."""

from django.apps import AppConfig


class InboxConfig(AppConfig):
    """Déclare le domaine de capture rapide des idées et actions."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inbox"
    verbose_name = "Boîte de réception"
