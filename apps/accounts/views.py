"""Vues des parcours liés au compte utilisateur."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm


def signup(request):
    """Crée un compte puis connecte immédiatement le nouvel utilisateur."""
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Votre compte a bien été créé.")
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    """Affiche et met à jour le profil de l'utilisateur connecté."""
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Votre profil a été mis à jour.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
