"""Tests métier, fonctionnels et de sécurité des projets."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import MacroActivity, Project

User = get_user_model()


class ProjectModelTests(TestCase):
    """Vérifie les règles métier portées par les modèles de projet."""

    @classmethod
    def setUpTestData(cls):
        """Crée le propriétaire commun aux tests du modèle."""
        cls.user = User.objects.create_user("owner@example.com", "test-password")

    def test_deadline_cannot_precede_start_date(self):
        """Un projet refuse une échéance antérieure à sa date de début."""
        project = Project(
            owner=self.user,
            name="Projet invalide",
            start_date=date.today(),
            deadline=date.today() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_progress_uses_completed_macro_activities(self):
        """La progression reflète la proportion d'activités terminées."""
        project = Project.objects.create(owner=self.user, name="Projet")
        MacroActivity.objects.create(
            project=project, title="Terminée", status=MacroActivity.Status.COMPLETED
        )
        MacroActivity.objects.create(project=project, title="À faire")

        self.assertEqual(project.progress, 50)

    def test_unfinished_macro_activity_is_actionable(self):
        """Une macro-activité sans tâche et non close est actionnable."""
        activity = MacroActivity(project=Project(owner=self.user), title="Action")

        self.assertTrue(activity.is_actionable)

    def test_active_task_makes_macro_activity_non_actionable(self):
        """Une activité possédant une tâche active n'est plus l'action directe."""
        from apps.tasks.models import Task

        project = Project.objects.create(owner=self.user, name="Projet avec tâche")
        activity = MacroActivity.objects.create(project=project, title="Lot")
        Task.objects.create(
            owner=self.user,
            project=project,
            macro_activity=activity,
            title="Action détaillée",
        )

        self.assertFalse(activity.is_actionable)

    def test_project_progress_prefers_tasks(self):
        """La progression utilise les tâches dès qu'elles sont présentes."""
        from apps.tasks.models import Task

        project = Project.objects.create(owner=self.user, name="Projet détaillé")
        MacroActivity.objects.create(
            project=project,
            title="Macro terminée",
            status=MacroActivity.Status.COMPLETED,
        )
        Task.objects.create(
            owner=self.user,
            project=project,
            title="Tâche terminée",
            status=Task.Status.COMPLETED,
        )
        Task.objects.create(owner=self.user, project=project, title="Tâche ouverte")

        self.assertEqual(project.progress, 50)


class ProjectPermissionTests(TestCase):
    """Garantit l'isolation complète des projets entre utilisateurs."""

    @classmethod
    def setUpTestData(cls):
        """Crée deux utilisateurs et un projet privé pour les scénarios."""
        cls.owner = User.objects.create_user("owner@example.com", "test-password")
        cls.other = User.objects.create_user("other@example.com", "test-password")
        cls.project = Project.objects.create(owner=cls.owner, name="Projet privé")
        cls.activity = MacroActivity.objects.create(
            project=cls.project, title="Activité privée"
        )

    def setUp(self):
        """Connecte l'utilisateur qui ne possède pas les données."""
        self.client.force_login(self.other)

    def test_other_user_cannot_view_project(self):
        """La consultation directe du projet d'un tiers retourne 404."""
        response = self.client.get(reverse("projects:detail", args=(self.project.id,)))

        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_update_project(self):
        """La modification directe du projet d'un tiers retourne 404."""
        response = self.client.post(
            reverse("projects:update", args=(self.project.id,)),
            {"name": "Projet détourné"},
        )

        self.assertEqual(response.status_code, 404)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Projet privé")

    def test_other_user_cannot_delete_activity(self):
        """La suppression directe de l'activité d'un tiers retourne 404."""
        response = self.client.post(
            reverse("projects:activity_delete", args=(self.activity.id,))
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MacroActivity.objects.filter(pk=self.activity.id).exists())


class ProjectViewsTests(TestCase):
    """Vérifie les principaux parcours utilisateur du module projets."""

    def setUp(self):
        """Crée et connecte le propriétaire utilisé dans chaque test."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.client.force_login(self.user)

    def test_create_project_assigns_authenticated_owner(self):
        """La création attribue automatiquement l'utilisateur connecté."""
        response = self.client.post(
            reverse("projects:create"),
            {
                "name": "Nouveau projet",
                "status": Project.Status.ACTIVE,
                "priority": Project.Priority.HIGH,
                "color": "#123456",
            },
        )

        project = Project.objects.get(name="Nouveau projet")
        self.assertEqual(project.owner, self.user)
        self.assertRedirects(response, reverse("projects:detail", args=(project.id,)))

    def test_archived_project_is_hidden_from_default_list(self):
        """Un projet archivé ne figure plus dans la liste opérationnelle."""
        project = Project.objects.create(
            owner=self.user, name="Ancien", status=Project.Status.ARCHIVED
        )

        response = self.client.get(reverse("projects:list"))

        self.assertNotContains(response, project.name)

    def test_archive_requires_post(self):
        """L'archivage est refusé pour une requête GET."""
        project = Project.objects.create(owner=self.user, name="À archiver")

        response = self.client.get(reverse("projects:archive", args=(project.id,)))

        self.assertEqual(response.status_code, 405)

    def test_delete_confirmation_does_not_delete_on_get(self):
        """La page GET confirme la suppression sans modifier les données."""
        project = Project.objects.create(owner=self.user, name="À conserver")

        response = self.client.get(reverse("projects:delete", args=(project.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Project.objects.filter(pk=project.id).exists())
