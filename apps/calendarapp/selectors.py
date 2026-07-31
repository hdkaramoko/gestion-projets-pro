"""Sélection et sérialisation des événements du calendrier."""

from datetime import datetime, time, timedelta
from typing import Any

from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.accounts.models import User
from apps.meetings.models import Meeting
from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task


def parse_calendar_range(
    *, start_value: str, end_value: str
) -> tuple[datetime, datetime]:
    """Valide et normalise les bornes ISO 8601 demandées par FullCalendar.

    La borne de fin est exclusive. Une plage supérieure à 370 jours est
    refusée afin de protéger l'endpoint contre une lecture excessive.

    Raises:
        ValueError: Si une date est absente, invalide ou si la plage est
            incohérente.
    """
    if not start_value or not end_value:
        raise ValueError("Les paramètres start et end sont obligatoires.")

    start = _parse_calendar_datetime(start_value)
    end = _parse_calendar_datetime(end_value)
    if start >= end:
        raise ValueError("La borne de fin doit être postérieure au début.")
    if end - start > timedelta(days=370):
        raise ValueError("La plage demandée ne peut pas dépasser 370 jours.")
    return start, end


def _parse_calendar_datetime(value: str) -> datetime:
    """Convertit une date ou date-heure ISO en date-heure consciente."""
    parsed_datetime = parse_datetime(value)
    if parsed_datetime is None:
        parsed_date = parse_date(value)
        if parsed_date is None:
            raise ValueError("Le format de date est invalide.")
        parsed_datetime = datetime.combine(parsed_date, time.min)
    if timezone.is_naive(parsed_datetime):
        parsed_datetime = timezone.make_aware(parsed_datetime)
    return parsed_datetime


def get_calendar_events(
    *, user: User, start: datetime, end: datetime
) -> list[dict[str, Any]]:
    """Retourne les événements calendrier appartenant à un utilisateur."""
    local_start = timezone.localtime(start).date()
    local_end = timezone.localtime(end).date()
    events: list[dict[str, Any]] = []

    tasks = (
        Task.objects.filter(owner=user)
        .exclude(project__status=Project.Status.ARCHIVED)
        .select_related("project")
    )
    planned_tasks = tasks.filter(
        planned_date__gte=local_start, planned_date__lt=local_end
    )
    deadline_tasks = tasks.filter(deadline__gte=local_start, deadline__lt=local_end)
    meetings = (
        Meeting.objects.filter(
            owner=user, scheduled_at__gte=start, scheduled_at__lt=end
        )
        .exclude(project__status=Project.Status.ARCHIVED)
        .select_related("project")
    )
    projects = Project.objects.filter(
        owner=user, deadline__gte=local_start, deadline__lt=local_end
    ).exclude(status=Project.Status.ARCHIVED)
    activities = (
        MacroActivity.objects.filter(
            project__owner=user,
            deadline__gte=local_start,
            deadline__lt=local_end,
        )
        .exclude(project__status=Project.Status.ARCHIVED)
        .select_related("project")
    )

    events.extend(_serialize_planned_task(task) for task in planned_tasks)
    events.extend(_serialize_task_deadline(task) for task in deadline_tasks)
    events.extend(_serialize_meeting(meeting) for meeting in meetings)
    events.extend(_serialize_project_deadline(project) for project in projects)
    events.extend(_serialize_activity_deadline(activity) for activity in activities)
    return events


def _serialize_planned_task(task: Task) -> dict[str, Any]:
    """Sérialise le jour de travail prévu pour une tâche déplaçable."""
    return {
        "id": f"task-planned-{task.id}",
        "title": f"À faire · {task.title}",
        "start": task.planned_date.isoformat(),
        "allDay": True,
        "url": reverse("tasks:detail", args=(task.id,)),
        "backgroundColor": task.project.color,
        "borderColor": task.project.color,
        "editable": True,
        "durationEditable": False,
        "extendedProps": {"kind": "task_planned", "taskId": str(task.id)},
    }


def _serialize_task_deadline(task: Task) -> dict[str, Any]:
    """Sérialise l'échéance non déplaçable d'une tâche."""
    return {
        "id": f"task-deadline-{task.id}",
        "title": f"Échéance · {task.title}",
        "start": task.deadline.isoformat(),
        "allDay": True,
        "url": reverse("tasks:detail", args=(task.id,)),
        "backgroundColor": "#dc3545",
        "borderColor": "#dc3545",
        "editable": False,
        "extendedProps": {"kind": "task_deadline"},
    }


def _serialize_meeting(meeting: Meeting) -> dict[str, Any]:
    """Sérialise une réunion à son heure locale."""
    return {
        "id": f"meeting-{meeting.id}",
        "title": f"Réunion · {meeting.title}",
        "start": timezone.localtime(meeting.scheduled_at).isoformat(),
        "allDay": False,
        "url": reverse("meetings:detail", args=(meeting.id,)),
        "backgroundColor": "#6f42c1",
        "borderColor": meeting.project.color,
        "editable": False,
        "extendedProps": {"kind": "meeting"},
    }


def _serialize_project_deadline(project: Project) -> dict[str, Any]:
    """Sérialise l'échéance d'un projet non archivé."""
    return {
        "id": f"project-{project.id}",
        "title": f"Projet · {project.name}",
        "start": project.deadline.isoformat(),
        "allDay": True,
        "url": reverse("projects:detail", args=(project.id,)),
        "backgroundColor": "#212529",
        "borderColor": project.color,
        "editable": False,
        "extendedProps": {"kind": "project_deadline"},
    }


def _serialize_activity_deadline(activity: MacroActivity) -> dict[str, Any]:
    """Sérialise l'échéance d'une macro-activité."""
    return {
        "id": f"activity-{activity.id}",
        "title": f"Macro · {activity.title}",
        "start": activity.deadline.isoformat(),
        "allDay": True,
        "url": reverse("projects:detail", args=(activity.project_id,)),
        "backgroundColor": "#fd7e14",
        "borderColor": activity.project.color,
        "editable": False,
        "extendedProps": {"kind": "activity_deadline"},
    }
