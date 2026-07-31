"""Vues transverses de l'application."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Affiche l'accueil authentifié en attendant le tableau de bord métier."""
    return render(request, "common/home.html")
