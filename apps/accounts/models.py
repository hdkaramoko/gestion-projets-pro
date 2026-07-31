"""Modèles liés aux comptes utilisateurs."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Utilisateur authentifié par son adresse email.

    Le champ historique ``username`` est supprimé afin que l'email constitue
    l'unique identifiant de connexion.
    """

    username = None
    email = models.EmailField("adresse email", unique=True)
    first_name = models.CharField("prénom", max_length=150, blank=True)
    last_name = models.CharField("nom", max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        """Définit les libellés français du modèle."""

        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self) -> str:
        """Retourne le nom complet ou, à défaut, l'adresse email."""
        return self.get_full_name().strip() or self.email
