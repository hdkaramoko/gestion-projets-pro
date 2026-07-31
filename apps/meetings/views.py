"""Vues sécurisées de gestion des réunions et de leurs actions."""

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MeetingActionForm, MeetingForm
from .selectors import get_meeting_actions_for_user, get_meetings_for_user
from .services import convert_meeting_action_to_task


@login_required
def meeting_list(request: HttpRequest) -> HttpResponse:
    """Liste les réunions avec recherche et filtre par projet."""
    meetings = get_meetings_for_user(user=request.user)
    query = request.GET.get("q", "").strip()
    if query:
        meetings = meetings.filter(
            Q(title__icontains=query)
            | Q(participants__icontains=query)
            | Q(project__name__icontains=query)
        )
    project = request.GET.get("project", "")
    if project:
        try:
            project_id = uuid.UUID(project)
        except ValueError:
            project_id = None
        if project_id:
            meetings = meetings.filter(project_id=project_id)
    projects = request.user.projects.exclude(status="archived")
    return render(
        request,
        "meetings/meeting_list.html",
        {
            "meetings": meetings,
            "projects": projects,
            "query": query,
            "selected_project": project,
        },
    )


@login_required
def meeting_detail(request: HttpRequest, meeting_id) -> HttpResponse:
    """Affiche un compte rendu et les actions accessibles au propriétaire."""
    meeting = get_object_or_404(get_meetings_for_user(user=request.user), pk=meeting_id)
    return render(request, "meetings/meeting_detail.html", {"meeting": meeting})


@login_required
def meeting_print(request: HttpRequest, meeting_id) -> HttpResponse:
    """Affiche une version épurée et imprimable du compte rendu."""
    meeting = get_object_or_404(get_meetings_for_user(user=request.user), pk=meeting_id)
    return render(request, "meetings/meeting_print.html", {"meeting": meeting})


@login_required
def meeting_create(request: HttpRequest) -> HttpResponse:
    """Crée une réunion en attribuant le propriétaire connecté."""
    initial = {}
    project_id = request.GET.get("project")
    if project_id:
        initial["project"] = project_id
    form = MeetingForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        meeting = form.save(commit=False)
        meeting.owner = request.user
        meeting.save()
        messages.success(request, "Le compte rendu a été créé.")
        return redirect("meetings:detail", meeting_id=meeting.id)
    return render(request, "meetings/meeting_form.html", {"form": form})


@login_required
def meeting_update(request: HttpRequest, meeting_id) -> HttpResponse:
    """Modifie une réunion appartenant à l'utilisateur."""
    meeting = get_object_or_404(get_meetings_for_user(user=request.user), pk=meeting_id)
    form = MeetingForm(
        request.POST or None,
        instance=meeting,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le compte rendu a été mis à jour.")
        return redirect("meetings:detail", meeting_id=meeting.id)
    return render(
        request,
        "meetings/meeting_form.html",
        {"form": form, "meeting": meeting},
    )


@login_required
def meeting_delete(request: HttpRequest, meeting_id) -> HttpResponse:
    """Confirme en GET puis supprime une réunion en POST."""
    meeting = get_object_or_404(get_meetings_for_user(user=request.user), pk=meeting_id)
    if request.method == "POST":
        meeting.delete()
        messages.success(request, "La réunion a été supprimée.")
        return redirect("meetings:list")
    return render(
        request,
        "meetings/meeting_confirm_delete.html",
        {"meeting": meeting},
    )


@login_required
def meeting_action_create(request: HttpRequest, meeting_id) -> HttpResponse:
    """Ajoute une action à une réunion de l'utilisateur."""
    meeting = get_object_or_404(get_meetings_for_user(user=request.user), pk=meeting_id)
    form = MeetingActionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action = form.save(commit=False)
        action.meeting = meeting
        action.save()
        messages.success(request, "L'action a été ajoutée.")
        return redirect("meetings:detail", meeting_id=meeting.id)
    return render(
        request,
        "meetings/action_form.html",
        {"form": form, "meeting": meeting},
    )


@login_required
def meeting_action_update(request: HttpRequest, action_id) -> HttpResponse:
    """Modifie une action issue d'une réunion de l'utilisateur."""
    action = get_object_or_404(
        get_meeting_actions_for_user(user=request.user), pk=action_id
    )
    form = MeetingActionForm(request.POST or None, instance=action)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "L'action a été mise à jour.")
        return redirect("meetings:detail", meeting_id=action.meeting_id)
    return render(
        request,
        "meetings/action_form.html",
        {"form": form, "meeting": action.meeting, "action": action},
    )


@require_POST
@login_required
def meeting_action_delete(request: HttpRequest, action_id) -> HttpResponse:
    """Supprime en POST une action accessible à l'utilisateur."""
    action = get_object_or_404(
        get_meeting_actions_for_user(user=request.user), pk=action_id
    )
    meeting_id = action.meeting_id
    action.delete()
    messages.success(request, "L'action a été supprimée.")
    return redirect("meetings:detail", meeting_id=meeting_id)


@require_POST
@login_required
def meeting_action_convert(request: HttpRequest, action_id) -> HttpResponse:
    """Convertit une action accessible en tâche, une seule fois."""
    action = get_object_or_404(
        get_meeting_actions_for_user(user=request.user), pk=action_id
    )
    try:
        task = convert_meeting_action_to_task(action=action)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("meetings:detail", meeting_id=action.meeting_id)
    messages.success(request, "L'action a été transformée en tâche.")
    return redirect("tasks:detail", task_id=task.id)
