"""Tests des sélecteurs, statistiques et permissions du tableau de bord."""

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task

from .selectors import (
    get_actionable_macro_activities,
    get_dashboard_statistics,
    get_overdue_macro_activities,
    get_overdue_tasks,
    get_projects_without_next_action,
    get_today_tasks,
    get_upcoming_deadlines,
    get_week_tasks,
)

User = get_user_model()


class DashboardSelectorsTests(TestCase):
    """Vérifie les règles temporelles et les prochaines actions."""

    def setUp(self):
        """Prépare un utilisateur, un projet actif et une date stable."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.project = Project.objects.create(
            owner=self.user,
            name="Projet actif",
            status=Project.Status.ACTIVE,
        )
        self.today = timezone.localdate()

    def create_task(self, title: str, **kwargs) -> Task:
        """Crée une tâche de test dans le projet principal."""
        return Task.objects.create(
            owner=self.user,
            project=self.project,
            title=title,
            **kwargs,
        )

    def test_overdue_tasks_only_include_active_past_deadlines(self):
        """Le retard exclut les tâches futures, terminées et abandonnées."""
        overdue = self.create_task("En retard", deadline=self.today - timedelta(days=1))
        self.create_task("Future", deadline=self.today + timedelta(days=1))
        self.create_task(
            "Terminée",
            deadline=self.today - timedelta(days=1),
            status=Task.Status.COMPLETED,
        )

        result = get_overdue_tasks(user=self.user, day=self.today)

        self.assertQuerySetEqual(result, [overdue], transform=lambda task: task)

    def test_today_tasks_are_not_duplicated(self):
        """Une tâche planifiée et due aujourd'hui n'apparaît qu'une fois."""
        task = self.create_task(
            "Double date", planned_date=self.today, deadline=self.today
        )

        result = get_today_tasks(user=self.user, day=self.today)

        self.assertQuerySetEqual(result, [task], transform=lambda item: item)

    def test_week_tasks_include_planning_or_deadline(self):
        """La semaine combine date planifiée et échéance sans doublon."""
        planned = self.create_task("Planifiée", planned_date=self.today)
        due = self.create_task("Due", deadline=self.today)
        self.create_task(
            "Plus tard",
            planned_date=self.today + timedelta(days=14),
        )

        result = get_week_tasks(user=self.user, day=self.today)

        self.assertSetEqual(set(result), {planned, due})

    def test_macro_activity_without_active_task_is_actionable(self):
        """Une activité ouverte redevient actionnable sans tâche active."""
        actionable = MacroActivity.objects.create(
            project=self.project, title="Action directe"
        )
        detailed = MacroActivity.objects.create(
            project=self.project, title="Action détaillée"
        )
        self.create_task("Sous-tâche", macro_activity=detailed)

        result = get_actionable_macro_activities(user=self.user)

        self.assertSetEqual(set(result), {actionable})

    def test_overdue_macro_activity_must_be_actionable(self):
        """Une activité échue avec tâche active n'est pas un retard autonome."""
        actionable = MacroActivity.objects.create(
            project=self.project,
            title="Macro en retard",
            deadline=self.today - timedelta(days=1),
        )
        detailed = MacroActivity.objects.create(
            project=self.project,
            title="Macro détaillée",
            deadline=self.today - timedelta(days=1),
        )
        self.create_task("Action active", macro_activity=detailed)

        result = get_overdue_macro_activities(user=self.user, day=self.today)

        self.assertQuerySetEqual(result, [actionable], transform=lambda item: item)

    def test_projects_without_next_action_respects_both_action_levels(self):
        """Seul un projet sans tâche active ni macro actionnable est signalé."""
        empty = Project.objects.create(
            owner=self.user,
            name="Sans action",
            status=Project.Status.ACTIVE,
        )
        with_task = Project.objects.create(
            owner=self.user,
            name="Avec tâche",
            status=Project.Status.ACTIVE,
        )
        Task.objects.create(owner=self.user, project=with_task, title="Action")
        with_macro = Project.objects.create(
            owner=self.user,
            name="Avec macro",
            status=Project.Status.ACTIVE,
        )
        MacroActivity.objects.create(project=with_macro, title="Macro")

        result = get_projects_without_next_action(user=self.user)

        self.assertSetEqual(set(result), {self.project, empty})

    def test_upcoming_deadlines_are_globally_chronological(self):
        """Les échéances de tous types sont fusionnées par date."""
        project = Project.objects.create(
            owner=self.user,
            name="Échéance projet",
            status=Project.Status.ACTIVE,
            deadline=self.today + timedelta(days=3),
        )
        task = self.create_task(
            "Échéance tâche", deadline=self.today + timedelta(days=1)
        )
        activity = MacroActivity.objects.create(
            project=self.project,
            title="Échéance macro",
            deadline=self.today + timedelta(days=2),
        )

        result = get_upcoming_deadlines(user=self.user, day=self.today)

        self.assertEqual(
            [item["object"] for item in result],
            [task, activity, project],
        )


class DashboardStatisticsTests(TestCase):
    """Vérifie les indicateurs agrégés affichés à l'utilisateur."""

    def test_statistics_compute_counts_load_and_on_time_rate(self):
        """Les statistiques respectent les statuts, dates et estimations."""
        user = User.objects.create_user("stats@example.com", "test-password")
        project = Project.objects.create(
            owner=user, name="Projet", status=Project.Status.ACTIVE
        )
        today = timezone.localdate()
        now = timezone.now()
        Task.objects.create(
            owner=user,
            project=project,
            title="Aujourd'hui en retard",
            planned_date=today,
            deadline=today - timedelta(days=1),
            estimated_load=45,
        )
        Task.objects.create(
            owner=user,
            project=project,
            title="En attente",
            status=Task.Status.WAITING,
            planned_date=today,
            estimated_load=15,
        )
        on_time_date = today - timedelta(days=2)
        Task.objects.create(
            owner=user,
            project=project,
            title="Terminée à temps",
            status=Task.Status.COMPLETED,
            deadline=on_time_date,
            completed_at=timezone.make_aware(
                datetime.combine(on_time_date, time(hour=12))
            ),
        )
        late_deadline = today - timedelta(days=3)
        Task.objects.create(
            owner=user,
            project=project,
            title="Terminée en retard",
            status=Task.Status.COMPLETED,
            deadline=late_deadline,
            completed_at=now,
        )

        statistics = get_dashboard_statistics(user=user, day=today)

        self.assertEqual(statistics["overdue_count"], 1)
        self.assertEqual(statistics["today_count"], 2)
        self.assertEqual(statistics["week_load"], 60)
        self.assertEqual(statistics["waiting_count"], 1)
        self.assertEqual(statistics["completed_last_7_days"], 2)
        self.assertEqual(statistics["on_time_rate"], 50)


class DashboardViewTests(TestCase):
    """Vérifie l'authentification et l'isolation de la page d'accueil."""

    def test_dashboard_requires_authentication(self):
        """Un visiteur anonyme est redirigé vers la connexion."""
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/")

    def test_dashboard_only_displays_current_users_data(self):
        """Le cockpit ne révèle aucun contenu appartenant à un tiers."""
        user = User.objects.create_user("pilot@example.com", "test-password")
        other = User.objects.create_user("other@example.com", "test-password")
        project = Project.objects.create(
            owner=user, name="Projet visible", status=Project.Status.ACTIVE
        )
        other_project = Project.objects.create(
            owner=other, name="Projet secret", status=Project.Status.ACTIVE
        )
        Task.objects.create(
            owner=user,
            project=project,
            title="Tâche visible",
            planned_date=timezone.localdate(),
        )
        Task.objects.create(
            owner=other,
            project=other_project,
            title="Tâche secrète",
            planned_date=timezone.localdate(),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Tâche visible")
        self.assertNotContains(response, "Tâche secrète")
