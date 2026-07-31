"""Vues sécurisées de consultation et de gestion des tâches."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.projects.models import Project

from .forms import TaskDateForm, TaskForm
from .selectors import filter_tasks, get_tasks_for_user
from .services import change_task_deadline, change_task_status, reschedule_task


@login_required
def task_list(request: HttpRequest) -> HttpResponse:
    """Liste et filtre toutes les tâches appartenant à l'utilisateur."""
    tasks = filter_tasks(
        tasks=get_tasks_for_user(user=request.user), params=request.GET
    )
    projects = Project.objects.filter(owner=request.user).exclude(
        status=Project.Status.ARCHIVED
    )
    return render(
        request,
        "tasks/task_list.html",
        {"tasks": tasks, "projects": projects, "filters": request.GET},
    )


@login_required
def task_detail(request: HttpRequest, task_id) -> HttpResponse:
    """Affiche une tâche uniquement lorsqu'elle appartient à l'utilisateur."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    return render(request, "tasks/task_detail.html", {"task": task})


@login_required
def task_create(request: HttpRequest) -> HttpResponse:
    """Crée une tâche pour l'utilisateur et un de ses projets."""
    initial = {}
    project_id = request.GET.get("project")
    if project_id:
        initial["project"] = project_id
    form = TaskForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.save()
        messages.success(request, "La tâche a été créée.")
        return redirect("tasks:detail", task_id=task.id)
    return render(request, "tasks/task_form.html", {"form": form})


@login_required
def task_update(request: HttpRequest, task_id) -> HttpResponse:
    """Modifie une tâche appartenant à l'utilisateur connecté."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    form = TaskForm(request.POST or None, instance=task, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La tâche a été mise à jour.")
        return redirect("tasks:detail", task_id=task.id)
    return render(request, "tasks/task_form.html", {"form": form, "task": task})


@login_required
def task_delete(request: HttpRequest, task_id) -> HttpResponse:
    """Confirme en GET puis supprime définitivement une tâche en POST."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    if request.method == "POST":
        task.delete()
        messages.success(request, "La tâche a été supprimée.")
        return redirect("tasks:list")
    return render(request, "tasks/task_confirm_delete.html", {"task": task})


@require_POST
@login_required
def task_status(request: HttpRequest, task_id, status: str) -> HttpResponse:
    """Applique rapidement un statut autorisé à une tâche accessible."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    try:
        change_task_status(task=task, status=status)
    except ValueError:
        messages.error(request, "Le statut demandé est invalide.")
    else:
        messages.success(
            request, f"La tâche est maintenant « {task.get_status_display()} »."
        )
    return redirect("tasks:detail", task_id=task.id)


@require_POST
@login_required
def task_reschedule(request: HttpRequest, task_id) -> HttpResponse:
    """Modifie uniquement la date planifiée d'une tâche accessible."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    form = TaskDateForm(request.POST)
    if form.is_valid():
        reschedule_task(task=task, planned_date=form.cleaned_data["date"])
        messages.success(request, "La date planifiée a été reportée.")
    else:
        messages.error(request, "La date planifiée fournie est invalide.")
    return redirect("tasks:detail", task_id=task.id)


@require_POST
@login_required
def task_deadline(request: HttpRequest, task_id) -> HttpResponse:
    """Modifie uniquement l'échéance d'une tâche accessible."""
    task = get_object_or_404(get_tasks_for_user(user=request.user), pk=task_id)
    form = TaskDateForm(request.POST)
    if form.is_valid():
        change_task_deadline(task=task, deadline=form.cleaned_data["date"])
        messages.success(request, "L'échéance a été mise à jour.")
    else:
        messages.error(request, "L'échéance fournie est invalide.")
    return redirect("tasks:detail", task_id=task.id)
