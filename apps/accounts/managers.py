"""Gestionnaire du modèle utilisateur personnalisé."""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Crée les utilisateurs identifiés par une adresse email."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Crée et enregistre un utilisateur standard.

        Args:
            email: Adresse email unique servant d'identifiant.
            password: Mot de passe brut, éventuellement absent.
            **extra_fields: Attributs supplémentaires du modèle.

        Returns:
            L'utilisateur nouvellement enregistré.
        """
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """Crée un administrateur possédant tous les droits Django."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Un superutilisateur doit avoir tous les droits.")
        return self.create_user(email, password, **extra_fields)
