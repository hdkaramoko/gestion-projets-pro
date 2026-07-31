"""Sélecteurs sécurisés et filtres de lecture des tâches."""

import uuid

from django import forms
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User

from .models import Task


def get_tasks_for_user(*, user: User) -> QuerySet[Task]:
    """Retourne les tâches d'un utilisateur avec leurs relations principales."""
    return Task.objects.filter(owner=user).select_related("project", "macro_activity")


def filter_tasks(*, tasks: QuerySet[Task], params) -> QuerySet[Task]:
    """Applique les filtres autorisés provenant d'une requête HTTP."""
    query = params.get("q", "").strip()
    if query:
        tasks = tasks.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    project = params.get("project", "")
    if project:
        try:
            project_id = uuid.UUID(project)
        except ValueError:
            project_id = None
        if project_id:
            tasks = tasks.filter(project_id=project_id)
    status = params.get("status", "")
    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    priority = params.get("priority", "")
    if priority in dict(Task._meta.get_field("priority").choices):
        tasks = tasks.filter(priority=priority)
    origin = params.get("origin", "")
    if origin in Task.Origin.values:
        tasks = tasks.filter(origin=origin)
    planned_date = params.get("planned_date", "")
    if planned_date:
        try:
            parsed_planned_date = forms.DateField().clean(planned_date)
        except forms.ValidationError:
            parsed_planned_date = None
        if parsed_planned_date:
            tasks = tasks.filter(planned_date=parsed_planned_date)
    deadline = params.get("deadline", "")
    if deadline:
        try:
            parsed_deadline = forms.DateField().clean(deadline)
        except forms.ValidationError:
            parsed_deadline = None
        if parsed_deadline:
            tasks = tasks.filter(deadline=parsed_deadline)
    if params.get("overdue") == "1":
        tasks = tasks.filter(deadline__lt=timezone.localdate()).exclude(
            status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED)
        )
    return tasks
