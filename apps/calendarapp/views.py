"""Vues HTML et JSON du calendrier."""

import json

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from apps.tasks.selectors import get_tasks_for_user
from apps.tasks.services import reschedule_task

from .selectors import get_calendar_events, parse_calendar_range


@login_required
def calendar_view(request: HttpRequest) -> HttpResponse:
    """Affiche les vues mensuelle, hebdomadaire et liste du calendrier."""
    return render(request, "calendarapp/calendar.html")


@require_GET
@login_required
def calendar_events(request: HttpRequest) -> JsonResponse:
    """Retourne le flux FullCalendar isolé pour l'utilisateur connecté.

    Les paramètres ``start`` et ``end`` sont des dates ISO 8601, avec une borne
    de fin exclusive.
    """
    try:
        start, end = parse_calendar_range(
            start_value=request.GET.get("start", ""),
            end_value=request.GET.get("end", ""),
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(
        get_calendar_events(user=request.user, start=start, end=end),
        safe=False,
    )


@require_POST
@login_required
def reschedule_calendar_task(request: HttpRequest, task_id) -> HttpResponse:
    """Met à jour la date planifiée d'une tâche après un glisser-déposer."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest("Le contenu JSON est invalide.")
    planned_date = parse_date(payload.get("planned_date", ""))
    if planned_date is None:
        return HttpResponseBadRequest("La date planifiée est invalide.")
    reschedule_task(task=task, planned_date=planned_date)
    return JsonResponse({"planned_date": planned_date.isoformat()})
