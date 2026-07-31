"""Vue principale du cockpit quotidien."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .selectors import (
    get_dashboard_statistics,
    get_overdue_macro_activities,
    get_overdue_tasks,
    get_projects_without_next_action,
    get_today_tasks,
    get_upcoming_deadlines,
    get_waiting_tasks,
    get_week_macro_activities,
    get_week_tasks,
)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Affiche les actions prioritaires et indicateurs de l'utilisateur."""
    user = request.user
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "overdue_tasks": get_overdue_tasks(user=user),
            "overdue_activities": get_overdue_macro_activities(user=user),
            "today_tasks": get_today_tasks(user=user),
            "week_tasks": get_week_tasks(user=user),
            "week_activities": get_week_macro_activities(user=user),
            "waiting_tasks": get_waiting_tasks(user=user),
            "upcoming_deadlines": get_upcoming_deadlines(user=user),
            "projects_without_action": get_projects_without_next_action(user=user),
            "statistics": get_dashboard_statistics(user=user),
        },
    )
