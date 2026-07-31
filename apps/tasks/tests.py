"""Tests métier, fonctionnels et de sécurité des tâches."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import MacroActivity, Project

from .forms import TaskForm
from .models import Task
from .services import change_task_deadline, change_task_status, reschedule_task

User = get_user_model()


class TaskModelTests(TestCase):
    """Vérifie les règles métier centrales du modèle Task."""

    @classmethod
    def setUpTestData(cls):
        """Prépare deux projets permettant les tests de cohérence."""
        cls.user = User.objects.create_user("owner@example.com", "test-password")
        cls.project = Project.objects.create(owner=cls.user, name="Projet A")
        cls.other_project = Project.objects.create(owner=cls.user, name="Projet B")

    def test_completed_task_gets_completion_date(self):
        """Une tâche terminée reçoit automatiquement une date de réalisation."""
        task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Action terminée",
            status=Task.Status.COMPLETED,
        )

        self.assertIsNotNone(task.completed_at)

    def test_reopened_task_loses_completion_date(self):
        """Une tâche rouverte perd automatiquement sa date de réalisation."""
        task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Action",
            status=Task.Status.COMPLETED,
        )

        change_task_status(task=task, status=Task.Status.IN_PROGRESS)

        self.assertIsNone(task.completed_at)

    def test_overdue_excludes_completed_and_cancelled_tasks(self):
        """Le retard ne concerne que les tâches actives après leur échéance."""
        task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Action en retard",
            deadline=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(task.is_overdue)

        change_task_status(task=task, status=Task.Status.COMPLETED)

        self.assertFalse(task.is_overdue)

    def test_macro_activity_must_belong_to_same_project(self):
        """Une activité provenant d'un autre projet est refusée."""
        activity = MacroActivity.objects.create(
            project=self.other_project, title="Mauvaise activité"
        )
        task = Task(
            owner=self.user,
            project=self.project,
            macro_activity=activity,
            title="Action incohérente",
        )

        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_project_must_belong_to_task_owner(self):
        """Une tâche ne peut pas pointer vers le projet d'un autre utilisateur."""
        other = User.objects.create_user("other@example.com", "test-password")
        task = Task(
            owner=other,
            project=self.project,
            title="Action sans droit",
        )

        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_planned_date_and_deadline_are_changed_independently(self):
        """Les services ne confondent jamais planification et échéance."""
        task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Action datée",
            planned_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=3),
        )
        new_planned_date = timezone.localdate() + timedelta(days=1)
        original_deadline = task.deadline

        reschedule_task(task=task, planned_date=new_planned_date)

        self.assertEqual(task.planned_date, new_planned_date)
        self.assertEqual(task.deadline, original_deadline)
        new_deadline = timezone.localdate() + timedelta(days=5)
        change_task_deadline(task=task, deadline=new_deadline)
        self.assertEqual(task.planned_date, new_planned_date)
        self.assertEqual(task.deadline, new_deadline)


class TaskFormTests(TestCase):
    """Vérifie que les relations proposées sont isolées par utilisateur."""

    def test_form_only_exposes_current_user_projects(self):
        """Un formulaire ne propose aucun projet appartenant à un tiers."""
        user = User.objects.create_user("owner@example.com", "test-password")
        other = User.objects.create_user("other@example.com", "test-password")
        visible = Project.objects.create(owner=user, name="Visible")
        Project.objects.create(owner=other, name="Masqué")

        form = TaskForm(user=user)

        self.assertQuerySetEqual(
            form.fields["project"].queryset, [visible], transform=lambda item: item
        )


class TaskViewsTests(TestCase):
    """Vérifie les parcours CRUD, les filtres et les permissions des tâches."""

    def setUp(self):
        """Crée deux utilisateurs et connecte le propriétaire principal."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.other = User.objects.create_user("other@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Mon projet")
        self.other_project = Project.objects.create(
            owner=self.other, name="Projet tiers"
        )
        self.task = Task.objects.create(
            owner=self.user, project=self.project, title="Ma tâche"
        )
        self.client.force_login(self.user)

    def test_create_task_assigns_authenticated_owner(self):
        """La création attribue le propriétaire depuis la session."""
        response = self.client.post(
            reverse("tasks:create"),
            {
                "project": self.project.id,
                "title": "Nouvelle tâche",
                "status": Task.Status.TODO,
                "priority": Project.Priority.NORMAL,
                "origin": Task.Origin.MANUAL,
            },
        )

        task = Task.objects.get(title="Nouvelle tâche")
        self.assertEqual(task.owner, self.user)
        self.assertRedirects(response, reverse("tasks:detail", args=(task.id,)))

    def test_user_cannot_view_another_users_task(self):
        """L'accès direct à la tâche d'un tiers retourne 404."""
        foreign_task = Task.objects.create(
            owner=self.other, project=self.other_project, title="Tâche privée"
        )

        response = self.client.get(reverse("tasks:detail", args=(foreign_task.id,)))

        self.assertEqual(response.status_code, 404)

    def test_quick_status_action_requires_post(self):
        """Une action rapide de statut refuse une requête GET."""
        response = self.client.get(
            reverse("tasks:status", args=(self.task.id, Task.Status.COMPLETED))
        )

        self.assertEqual(response.status_code, 405)

    def test_overdue_filter_only_returns_overdue_active_tasks(self):
        """Le filtre retard écarte les tâches futures et terminées."""
        self.task.deadline = timezone.localdate() - timedelta(days=1)
        self.task.save()
        Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Tâche future",
            deadline=timezone.localdate() + timedelta(days=1),
        )

        response = self.client.get(reverse("tasks:list"), {"overdue": "1"})

        self.assertContains(response, "Ma tâche")
        self.assertNotContains(response, "Tâche future")

    def test_invalid_filter_values_do_not_crash(self):
        """Des paramètres de filtre manipulés restent sans effet dangereux."""
        response = self.client.get(
            reverse("tasks:list"),
            {"project": "invalide", "planned_date": "demain"},
        )

        self.assertEqual(response.status_code, 200)
