"""Tests métier, fonctionnels et de sécurité de la boîte de réception."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task

from .forms import InboxConversionForm
from .models import InboxItem
from .services import convert_inbox_item_to_task

User = get_user_model()


class InboxConversionTests(TestCase):
    """Vérifie la transformation fiable d'une capture en tâche."""

    def setUp(self):
        """Prépare un utilisateur, un projet et une capture à qualifier."""
        self.user = User.objects.create_user("owner@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Projet")
        self.activity = MacroActivity.objects.create(
            project=self.project, title="Activité"
        )
        self.item = InboxItem.objects.create(
            owner=self.user, content="Préparer la synthèse"
        )

    def convert(self) -> Task:
        """Transforme la capture commune avec des valeurs de test cohérentes."""
        return convert_inbox_item_to_task(
            item=self.item,
            project=self.project,
            macro_activity=self.activity,
            priority=Project.Priority.HIGH,
            planned_date=timezone.localdate() + timedelta(days=1),
            deadline=timezone.localdate() + timedelta(days=3),
        )

    def test_conversion_creates_linked_inbox_task(self):
        """La tâche reprend les choix et conserve un lien vers la capture."""
        task = self.convert()
        self.item.refresh_from_db()

        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.title, self.item.content)
        self.assertEqual(task.origin, Task.Origin.INBOX)
        self.assertEqual(task.macro_activity, self.activity)
        self.assertEqual(self.item.status, InboxItem.Status.CONVERTED)
        self.assertEqual(self.item.converted_task, task)
        self.assertIsNotNone(self.item.processed_at)

    def test_item_cannot_be_converted_twice(self):
        """Une seconde conversion du même élément est explicitement refusée."""
        self.convert()

        with self.assertRaises(ValueError):
            self.convert()

        self.assertEqual(Task.objects.count(), 1)

    def test_conversion_rejects_another_users_project(self):
        """La couche métier refuse un projet appartenant à un autre compte."""
        other = User.objects.create_user("other@example.com", "test-password")
        foreign_project = Project.objects.create(owner=other, name="Projet tiers")

        with self.assertRaises(ValueError):
            convert_inbox_item_to_task(
                item=self.item,
                project=foreign_project,
                macro_activity=None,
                priority=Project.Priority.NORMAL,
                planned_date=None,
                deadline=None,
            )


class InboxFormTests(TestCase):
    """Vérifie l'isolation des choix proposés pendant la qualification."""

    def test_conversion_form_only_exposes_users_projects(self):
        """Le formulaire masque les projets appartenant à un autre utilisateur."""
        user = User.objects.create_user("owner@example.com", "test-password")
        other = User.objects.create_user("other@example.com", "test-password")
        visible = Project.objects.create(owner=user, name="Visible")
        Project.objects.create(owner=other, name="Masqué")

        form = InboxConversionForm(user=user)

        self.assertQuerySetEqual(
            form.fields["project"].queryset,
            [visible],
            transform=lambda project: project,
        )


class InboxViewsTests(TestCase):
    """Vérifie les parcours HTTP et l'isolation de la boîte de réception."""

    def setUp(self):
        """Crée deux utilisateurs et connecte le propriétaire principal."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.other = User.objects.create_user("other@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Mon projet")
        self.item = InboxItem.objects.create(owner=self.user, content="Mon élément")
        self.foreign_item = InboxItem.objects.create(
            owner=self.other, content="Élément privé"
        )
        self.client.force_login(self.user)

    def test_quick_capture_assigns_authenticated_owner(self):
        """La capture rapide attribue l'utilisateur depuis la session."""
        response = self.client.post(reverse("inbox:list"), {"content": "Nouvelle idée"})

        self.assertRedirects(response, reverse("inbox:list"))
        item = InboxItem.objects.get(content="Nouvelle idée")
        self.assertEqual(item.owner, self.user)

    def test_list_does_not_show_another_users_item(self):
        """La liste ne révèle jamais le contenu d'un autre compte."""
        response = self.client.get(reverse("inbox:list"))

        self.assertContains(response, self.item.content)
        self.assertNotContains(response, self.foreign_item.content)

    def test_user_cannot_convert_another_users_item(self):
        """L'accès direct à la qualification d'un tiers retourne 404."""
        response = self.client.get(
            reverse("inbox:convert", args=(self.foreign_item.id,))
        )

        self.assertEqual(response.status_code, 404)

    def test_conversion_view_creates_task(self):
        """Une qualification valide redirige vers la tâche créée."""
        response = self.client.post(
            reverse("inbox:convert", args=(self.item.id,)),
            {
                "project": self.project.id,
                "priority": Project.Priority.NORMAL,
            },
        )

        task = Task.objects.get(title=self.item.content)
        self.assertRedirects(response, reverse("tasks:detail", args=(task.id,)))

    def test_ignore_requires_post(self):
        """L'action ignorer refuse les requêtes GET."""
        response = self.client.get(reverse("inbox:ignore", args=(self.item.id,)))

        self.assertEqual(response.status_code, 405)

    def test_delete_requires_post(self):
        """La suppression refuse les requêtes GET et conserve l'élément."""
        response = self.client.get(reverse("inbox:delete", args=(self.item.id,)))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(InboxItem.objects.filter(pk=self.item.id).exists())
