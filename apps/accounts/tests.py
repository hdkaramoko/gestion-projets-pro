"""Tests du modèle utilisateur et des parcours d'authentification."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    """Vérifie la création et l'identification des utilisateurs par email."""

    def test_create_user_with_email(self):
        """Un utilisateur est créé sans nom d'utilisateur historique."""
        user = User.objects.create_user("Test@Example.com", "mot-de-passe-solide")

        self.assertEqual(user.email, "Test@example.com")
        self.assertIsNone(user.username)
        self.assertTrue(user.check_password("mot-de-passe-solide"))

    def test_email_is_required(self):
        """La création sans adresse email est refusée explicitement."""
        with self.assertRaisesMessage(ValueError, "email est obligatoire"):
            User.objects.create_user("", "mot-de-passe-solide")


class AuthenticationViewsTests(TestCase):
    """Vérifie l'inscription, la connexion et la protection des pages privées."""

    def test_home_redirects_anonymous_user(self):
        """L'accueil redirige un visiteur anonyme vers la connexion."""
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/")

    def test_signup_logs_user_in(self):
        """Une inscription valide ouvre immédiatement la session."""
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "nouveau@example.com",
                "first_name": "Camille",
                "last_name": "Martin",
                "password1": "mot-de-passe-de-test-2026",
                "password2": "mot-de-passe-de-test-2026",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(email="nouveau@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_uses_email(self):
        """La connexion accepte l'email comme identifiant unique."""
        User.objects.create_user("camille@example.com", "mot-de-passe-de-test-2026")

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "camille@example.com",
                "password": "mot-de-passe-de-test-2026",
            },
        )

        self.assertRedirects(response, reverse("home"))
