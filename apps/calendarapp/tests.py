"""Tests du flux JSON et des interactions du calendrier."""

import json
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.meetings.models import Meeting
from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task

from .selectors import parse_calendar_range

User = get_user_model()


class CalendarRangeTests(TestCase):
    """Vérifie la validation des bornes transmises par FullCalendar."""

    def test_valid_iso_range_is_parsed(self):
        """Une plage ISO cohérente retourne deux dates-heures conscientes."""
        start, end = parse_calendar_range(
            start_value="2026-08-01T00:00:00+02:00",
            end_value="2026-09-01T00:00:00+02:00",
        )

        self.assertTrue(timezone.is_aware(start))
        self.assertTrue(timezone.is_aware(end))

    def test_missing_or_invalid_range_is_rejected(self):
        """Une borne absente, illisible ou inversée est refusée."""
        invalid_ranges = (
            ("", "2026-09-01"),
            ("demain", "2026-09-01"),
            ("2026-09-01", "2026-08-01"),
            ("2026-01-01", "2028-01-01"),
        )

        for start, end in invalid_ranges:
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    parse_calendar_range(start_value=start, end_value=end)


class CalendarEndpointTests(TestCase):
    """Vérifie le contenu, les bornes et l'isolation du flux JSON."""

    def setUp(self):
        """Prépare des événements appartenant à deux utilisateurs."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.other = User.objects.create_user("other@example.com", "test-password")
        self.start_date = timezone.localdate()
        self.end_date = self.start_date + timedelta(days=10)
        self.project = Project.objects.create(
            owner=self.user,
            name="Projet visible",
            status=Project.Status.ACTIVE,
            deadline=self.start_date + timedelta(days=4),
            color="#123456",
        )
        self.other_project = Project.objects.create(
            owner=self.other,
            name="Projet secret",
            status=Project.Status.ACTIVE,
            deadline=self.start_date + timedelta(days=4),
        )
        self.task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="Tâche visible",
            planned_date=self.start_date + timedelta(days=1),
            deadline=self.start_date + timedelta(days=2),
        )
        Task.objects.create(
            owner=self.other,
            project=self.other_project,
            title="Tâche secrète",
            planned_date=self.start_date + timedelta(days=1),
        )
        self.activity = MacroActivity.objects.create(
            project=self.project,
            title="Macro visible",
            deadline=self.start_date + timedelta(days=3),
        )
        meeting_datetime = timezone.make_aware(
            datetime.combine(self.start_date + timedelta(days=2), time(hour=10))
        )
        self.meeting = Meeting.objects.create(
            owner=self.user,
            project=self.project,
            title="Réunion visible",
            scheduled_at=meeting_datetime,
        )
        self.client.force_login(self.user)

    def get_events(self, **params):
        """Interroge le flux avec une plage valide par défaut."""
        query = {
            "start": self.start_date.isoformat(),
            "end": self.end_date.isoformat(),
        }
        query.update(params)
        return self.client.get(reverse("calendar:events"), query)

    def test_endpoint_returns_all_supported_event_types(self):
        """Le flux contient planification, échéances, réunion, projet et macro."""
        response = self.get_events()

        self.assertEqual(response.status_code, 200)
        events = response.json()
        kinds = {event["extendedProps"]["kind"] for event in events}
        self.assertSetEqual(
            kinds,
            {
                "task_planned",
                "task_deadline",
                "meeting",
                "project_deadline",
                "activity_deadline",
            },
        )
        planned_event = next(
            event
            for event in events
            if event["extendedProps"]["kind"] == "task_planned"
        )
        self.assertTrue(planned_event["editable"])
        self.assertEqual(planned_event["backgroundColor"], self.project.color)
        deadline_event = next(
            event
            for event in events
            if event["extendedProps"]["kind"] == "task_deadline"
        )
        self.assertFalse(deadline_event["editable"])

    def test_endpoint_never_returns_another_users_events(self):
        """Les titres appartenant à un autre utilisateur sont absents."""
        response = self.get_events()

        titles = " ".join(event["title"] for event in response.json())
        self.assertIn("Tâche visible", titles)
        self.assertNotIn("Tâche secrète", titles)
        self.assertNotIn("Projet secret", titles)

    def test_endpoint_uses_exclusive_end_bound(self):
        """Un événement placé sur la borne de fin n'est pas retourné."""
        boundary_task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="À la limite",
            planned_date=self.end_date,
        )

        response = self.get_events()

        ids = {event["id"] for event in response.json()}
        self.assertNotIn(f"task-planned-{boundary_task.id}", ids)

    def test_invalid_parameters_return_bad_request(self):
        """Une plage invalide produit une réponse JSON 400 explicite."""
        response = self.get_events(start="date-invalide")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_endpoint_requires_authentication(self):
        """Le flux redirige un utilisateur non authentifié."""
        self.client.logout()

        response = self.get_events()

        self.assertEqual(response.status_code, 302)


class CalendarRescheduleTests(TestCase):
    """Vérifie le déplacement sécurisé des dates planifiées."""

    def setUp(self):
        """Crée une tâche visible et une tâche appartenant à un tiers."""
        self.user = User.objects.create_user("pilot@example.com", "test-password")
        self.other = User.objects.create_user("other@example.com", "test-password")
        self.project = Project.objects.create(owner=self.user, name="Projet")
        self.other_project = Project.objects.create(owner=self.other, name="Tiers")
        self.task = Task.objects.create(
            owner=self.user,
            project=self.project,
            title="À déplacer",
            planned_date=timezone.localdate(),
            deadline=timezone.localdate() + timedelta(days=5),
        )
        self.foreign_task = Task.objects.create(
            owner=self.other,
            project=self.other_project,
            title="Privée",
        )
        self.client.force_login(self.user)

    def post_date(self, task: Task, value: str):
        """Envoie une nouvelle date au format JSON."""
        return self.client.post(
            reverse("calendar:reschedule_task", args=(task.id,)),
            data=json.dumps({"planned_date": value}),
            content_type="application/json",
        )

    def test_reschedule_changes_planned_date_only(self):
        """Le déplacement ne modifie jamais l'échéance."""
        new_date = timezone.localdate() + timedelta(days=2)
        original_deadline = self.task.deadline

        response = self.post_date(self.task, new_date.isoformat())

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.planned_date, new_date)
        self.assertEqual(self.task.deadline, original_deadline)

    def test_user_cannot_reschedule_another_users_task(self):
        """Le déplacement direct d'une tâche tierce retourne 404."""
        response = self.post_date(self.foreign_task, timezone.localdate().isoformat())

        self.assertEqual(response.status_code, 404)

    def test_invalid_json_or_date_is_rejected(self):
        """Un corps JSON illisible ou une date invalide retourne 400."""
        invalid_date = self.post_date(self.task, "demain")
        invalid_json = self.client.post(
            reverse("calendar:reschedule_task", args=(self.task.id,)),
            data="{",
            content_type="application/json",
        )

        self.assertEqual(invalid_date.status_code, 400)
        self.assertEqual(invalid_json.status_code, 400)

    def test_reschedule_requires_post(self):
        """Le déplacement d'une tâche refuse une requête GET."""
        response = self.client.get(
            reverse("calendar:reschedule_task", args=(self.task.id,))
        )

        self.assertEqual(response.status_code, 405)


class CalendarViewTests(TestCase):
    """Vérifie l'accès à la page FullCalendar."""

    def test_calendar_page_requires_login_and_loads_fullcalendar(self):
        """La page protégée contient le conteneur et le script FullCalendar."""
        user = User.objects.create_user("pilot@example.com", "test-password")
        anonymous_response = self.client.get(reverse("calendar:view"))
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(user)
        response = self.client.get(reverse("calendar:view"))

        self.assertContains(response, 'id="calendar"')
        self.assertContains(response, "fullcalendar@6.1.19")
