"""Configuration de l'application des comptes."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Déclare l'application responsable des comptes utilisateurs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Comptes"
