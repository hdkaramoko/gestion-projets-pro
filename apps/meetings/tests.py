"""Tests métier, fonctionnels et de sécurité des réunions."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Project
from apps.tasks.models import Task

from .forms import MeetingForm
from .models import Meeting, MeetingAction
from .services import convert_meeting_action_to_task

User = get_user_model()


class MeetingModelTests(TestCase):
    """Vérifie la cohérence entre réunion, propriétaire et projet."""

    def test_meeting_rejects_another_users_project(self):
        """Une réunion ne peut pas utiliser le projet d'un tiers."""
        owner = User.objects.create_user("owner@example.com", "test-password")
        other = User.objects.create_user("other@example.com", "test-password")
        project = Project.objects.create(owner=owner, name="Projet privé")
        meeting = Meeting(
            owner=other,
            project=project,
            title="Réunion incohérente",
            scheduled_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            meeting.full_clean()


class MeetingConversionTests(TestCase):
    """Vérifie la conversion unique d'une action de réunion en tâche."""

    def setUp(self):
        """Prépare une réunion et une action complète à convertir."""
        self.user = User.objects.create_user("owner@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Projet")
        self.meeting = Meeting.objects.create(
            owner=self.user,
            project=self.project,
            title="Comité",
            scheduled_at=timezone.now(),
        )
        self.action = MeetingAction.objects.create(
            meeting=self.meeting,
            title="Envoyer la synthèse",
            description="Préparer et diffuser le document.",
            assignee="Camille",
            deadline=timezone.localdate() + timedelta(days=2),
            priority=Project.Priority.HIGH,
        )

    def test_conversion_copies_expected_fields_and_reference(self):
        """La tâche reprend le projet, le contenu, l'échéance et la priorité."""
        task = convert_meeting_action_to_task(action=self.action)
        self.action.refresh_from_db()

        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.title, self.action.title)
        self.assertEqual(task.description, self.action.description)
        self.assertEqual(task.deadline, self.action.deadline)
        self.assertEqual(task.priority, self.action.priority)
        self.assertEqual(task.origin, Task.Origin.MEETING)
        self.assertEqual(self.action.created_task, task)

    def test_action_cannot_be_converted_twice(self):
        """Une seconde conversion ne crée aucune tâche supplémentaire."""
        convert_meeting_action_to_task(action=self.action)

        with self.assertRaises(ValueError):
            convert_meeting_action_to_task(action=self.action)

        self.assertEqual(Task.objects.count(), 1)


class MeetingFormTests(TestCase):
    """Vérifie l'isolation des projets proposés dans les formulaires."""

    def test_form_only_exposes_current_users_projects(self):
        """Le formulaire de réunion masque les projets des autres comptes."""
        user = User.objects.create_user("owner@example.com", "test-password")
        other = User.objects.create_user("other@example.com", "test-password")
        visible = Project.objects.create(owner=user, name="Visible")
        Project.objects.create(owner=other, name="Masqué")

        form = MeetingForm(user=user)

        self.assertQuerySetEqual(
            form.fields["project"].queryset,
            [visible],
            transform=lambda project: project,
        )


class MeetingViewsTests(TestCase):
    """Vérifie les parcours HTTP et les protections des comptes rendus."""

    def setUp(self):
        """Crée deux espaces utilisateurs et connecte le premier."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.other = User.objects.create_user("other@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Mon projet")
        self.other_project = Project.objects.create(
            owner=self.other, name="Projet tiers"
        )
        self.meeting = Meeting.objects.create(
            owner=self.user,
            project=self.project,
            title="Ma réunion",
            scheduled_at=timezone.now(),
        )
        self.foreign_meeting = Meeting.objects.create(
            owner=self.other,
            project=self.other_project,
            title="Réunion privée",
            scheduled_at=timezone.now(),
        )
        self.action = MeetingAction.objects.create(
            meeting=self.meeting, title="Mon action"
        )
        self.foreign_action = MeetingAction.objects.create(
            meeting=self.foreign_meeting, title="Action privée"
        )
        self.client.force_login(self.user)

    def test_create_meeting_assigns_authenticated_owner(self):
        """La création attribue toujours le propriétaire depuis la session."""
        response = self.client.post(
            reverse("meetings:create"),
            {
                "project": self.project.id,
                "title": "Nouvelle réunion",
                "scheduled_at": "2026-08-01T10:30",
            },
        )

        meeting = Meeting.objects.get(title="Nouvelle réunion")
        self.assertEqual(meeting.owner, self.user)
        self.assertRedirects(response, reverse("meetings:detail", args=(meeting.id,)))

    def test_list_hides_another_users_meeting(self):
        """La liste n'affiche aucun compte rendu d'un autre utilisateur."""
        response = self.client.get(reverse("meetings:list"))

        self.assertContains(response, self.meeting.title)
        self.assertNotContains(response, self.foreign_meeting.title)

    def test_user_cannot_view_another_users_meeting(self):
        """L'accès direct au compte rendu d'un tiers retourne 404."""
        response = self.client.get(
            reverse("meetings:detail", args=(self.foreign_meeting.id,))
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_convert_another_users_action(self):
        """La conversion directe de l'action d'un tiers retourne 404."""
        response = self.client.post(
            reverse("meetings:action_convert", args=(self.foreign_action.id,))
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Task.objects.exists())

    def test_conversion_requires_post(self):
        """La conversion d'une action refuse une requête GET."""
        response = self.client.get(
            reverse("meetings:action_convert", args=(self.action.id,))
        )

        self.assertEqual(response.status_code, 405)

    def test_print_view_is_protected_and_contains_report(self):
        """La vue imprimable restitue le compte rendu accessible."""
        response = self.client.get(reverse("meetings:print", args=(self.meeting.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.meeting.title)
        self.assertContains(response, self.action.title)

    def test_delete_get_only_displays_confirmation(self):
        """Une requête GET ne supprime pas la réunion."""
        response = self.client.get(reverse("meetings:delete", args=(self.meeting.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Meeting.objects.filter(pk=self.meeting.id).exists())
