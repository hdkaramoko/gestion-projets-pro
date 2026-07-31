"""Sélecteurs et indicateurs centralisés du tableau de bord."""

from datetime import date, timedelta
from typing import Any

from django.db.models import Exists, OuterRef, Q, QuerySet, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task

INACTIVE_TASK_STATUSES = (Task.Status.COMPLETED, Task.Status.CANCELLED)
INACTIVE_ACTIVITY_STATUSES = (
    MacroActivity.Status.COMPLETED,
    MacroActivity.Status.CANCELLED,
)


def get_week_bounds(day: date | None = None) -> tuple[date, date]:
    """Retourne le lundi et le dimanche de la semaine contenant une date."""
    current_day = day or timezone.localdate()
    start = current_day - timedelta(days=current_day.weekday())
    return start, start + timedelta(days=6)


def get_overdue_tasks(*, user: User, day: date | None = None) -> QuerySet[Task]:
    """Retourne les tâches actives dont l'échéance est strictement dépassée."""
    current_day = day or timezone.localdate()
    return (
        Task.objects.filter(owner=user, deadline__lt=current_day)
        .exclude(status__in=INACTIVE_TASK_STATUSES)
        .select_related("project", "macro_activity")
    )


def get_actionable_macro_activities(*, user: User) -> QuerySet[MacroActivity]:
    """Retourne les macro-activités ouvertes ne contenant aucune tâche active."""
    active_tasks = Task.objects.filter(
        macro_activity_id=OuterRef("pk"),
    ).exclude(status__in=INACTIVE_TASK_STATUSES)
    return (
        MacroActivity.objects.filter(project__owner=user)
        .exclude(status__in=INACTIVE_ACTIVITY_STATUSES)
        .annotate(has_active_task=Exists(active_tasks))
        .filter(has_active_task=False)
        .select_related("project")
    )


def get_overdue_macro_activities(
    *, user: User, day: date | None = None
) -> QuerySet[MacroActivity]:
    """Retourne les macro-activités actionnables dont l'échéance est dépassée."""
    current_day = day or timezone.localdate()
    return get_actionable_macro_activities(user=user).filter(deadline__lt=current_day)


def get_today_tasks(*, user: User, day: date | None = None) -> QuerySet[Task]:
    """Retourne sans doublon les tâches planifiées ou dues à une date."""
    current_day = day or timezone.localdate()
    return (
        Task.objects.filter(owner=user)
        .exclude(status__in=INACTIVE_TASK_STATUSES)
        .filter(Q(planned_date=current_day) | Q(deadline=current_day))
        .select_related("project", "macro_activity")
        .distinct()
    )


def get_week_tasks(*, user: User, day: date | None = None) -> QuerySet[Task]:
    """Retourne les tâches planifiées ou dues pendant la semaine courante."""
    start, end = get_week_bounds(day)
    return (
        Task.objects.filter(owner=user)
        .exclude(status__in=INACTIVE_TASK_STATUSES)
        .filter(Q(planned_date__range=(start, end)) | Q(deadline__range=(start, end)))
        .select_related("project", "macro_activity")
        .distinct()
    )


def get_week_macro_activities(
    *, user: User, day: date | None = None
) -> QuerySet[MacroActivity]:
    """Retourne les macro-activités actionnables dues pendant la semaine."""
    start, end = get_week_bounds(day)
    return get_actionable_macro_activities(user=user).filter(
        deadline__range=(start, end)
    )


def get_waiting_tasks(*, user: User) -> QuerySet[Task]:
    """Retourne les tâches en attente, des plus anciennes aux plus récentes."""
    return (
        Task.objects.filter(owner=user, status=Task.Status.WAITING)
        .select_related("project")
        .order_by("created_at")
    )


def get_projects_without_next_action(*, user: User) -> QuerySet[Project]:
    """Retourne les projets actifs sans tâche active ni activité actionnable."""
    active_tasks = Task.objects.filter(project_id=OuterRef("pk")).exclude(
        status__in=INACTIVE_TASK_STATUSES
    )
    activity_active_tasks = Task.objects.filter(
        macro_activity_id=OuterRef("pk")
    ).exclude(status__in=INACTIVE_TASK_STATUSES)
    actionable_activities = (
        MacroActivity.objects.filter(project_id=OuterRef("pk"))
        .exclude(status__in=INACTIVE_ACTIVITY_STATUSES)
        .annotate(has_active_task=Exists(activity_active_tasks))
        .filter(has_active_task=False)
    )
    return (
        Project.objects.filter(owner=user, status=Project.Status.ACTIVE)
        .annotate(
            has_active_task=Exists(active_tasks),
            has_actionable_activity=Exists(actionable_activities),
        )
        .filter(has_active_task=False, has_actionable_activity=False)
    )


def get_upcoming_deadlines(
    *, user: User, day: date | None = None
) -> list[dict[str, Any]]:
    """Retourne toutes les prochaines échéances dans l'ordre chronologique."""
    current_day = day or timezone.localdate()
    tasks = (
        Task.objects.filter(owner=user, deadline__gte=current_day)
        .exclude(status__in=INACTIVE_TASK_STATUSES)
        .select_related("project")
        .order_by("deadline")
    )
    activities = get_actionable_macro_activities(user=user).filter(
        deadline__gte=current_day
    )
    projects = Project.objects.filter(
        owner=user,
        deadline__gte=current_day,
        status__in=(
            Project.Status.UPCOMING,
            Project.Status.ACTIVE,
            Project.Status.PAUSED,
        ),
    ).order_by("deadline")
    deadlines = [
        {"kind": "task", "object": task, "deadline": task.deadline} for task in tasks
    ]
    deadlines.extend(
        {"kind": "activity", "object": activity, "deadline": activity.deadline}
        for activity in activities
    )
    deadlines.extend(
        {"kind": "project", "object": project, "deadline": project.deadline}
        for project in projects
    )
    return sorted(deadlines, key=lambda item: item["deadline"])


def get_dashboard_statistics(*, user: User, day: date | None = None) -> dict[str, Any]:
    """Calcule les indicateurs utiles du tableau de bord.

    Le taux de respect des délais porte uniquement sur les tâches terminées
    possédant une échéance.
    """
    current_day = day or timezone.localdate()
    week_start, week_end = get_week_bounds(current_day)
    week_tasks = get_week_tasks(user=user, day=current_day)
    completed_since = timezone.now() - timedelta(days=7)
    completed_with_deadline = Task.objects.filter(
        owner=user,
        status=Task.Status.COMPLETED,
        completed_at__isnull=False,
        deadline__isnull=False,
    )
    completed_on_time = sum(
        1
        for task in completed_with_deadline
        if timezone.localtime(task.completed_at).date() <= task.deadline
    )
    completed_total = completed_with_deadline.count()
    on_time_rate = (
        round(completed_on_time * 100 / completed_total) if completed_total else 0
    )
    return {
        "overdue_count": get_overdue_tasks(user=user, day=current_day).count(),
        "today_count": get_today_tasks(user=user, day=current_day).count(),
        "week_count": week_tasks.count(),
        "completed_last_7_days": Task.objects.filter(
            owner=user,
            status=Task.Status.COMPLETED,
            completed_at__gte=completed_since,
        ).count(),
        "on_time_rate": on_time_rate,
        "week_load": week_tasks.aggregate(total=Sum("estimated_load"))["total"] or 0,
        "waiting_count": get_waiting_tasks(user=user).count(),
        "projects_without_action_count": get_projects_without_next_action(
            user=user
        ).count(),
        "week_start": week_start,
        "week_end": week_end,
    }
