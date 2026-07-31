"""Formulaires d'inscription et de profil."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    """Inscrit un utilisateur avec son email et son identité facultative."""

    class Meta(UserCreationForm.Meta):
        """Sélectionne les champs affichés lors de l'inscription."""

        model = User
        fields = ("email", "first_name", "last_name")


class ProfileForm(forms.ModelForm):
    """Permet à l'utilisateur connecté de modifier son profil."""

    class Meta:
        """Limite l'édition aux informations personnelles autorisées."""

        model = User
        fields = ("email", "first_name", "last_name")
