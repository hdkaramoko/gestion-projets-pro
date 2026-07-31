"""Vues sécurisées de gestion des projets et macro-activités."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MacroActivityForm, ProjectForm
from .models import Project
from .selectors import get_macro_activities_for_user, get_projects_for_user
from .services import archive_project, reactivate_project


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """Liste les projets actifs de l'utilisateur avec recherche et filtre."""
    projects = get_projects_for_user(user=request.user)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        projects = projects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if status in Project.Status.values and status != Project.Status.ARCHIVED:
        projects = projects.filter(status=status)
    return render(
        request,
        "projects/project_list.html",
        {"projects": projects, "query": query, "selected_status": status},
    )


@login_required
def archived_project_list(request: HttpRequest) -> HttpResponse:
    """Liste uniquement les projets archivés de l'utilisateur."""
    projects = get_projects_for_user(user=request.user, include_archived=True).filter(
        status=Project.Status.ARCHIVED
    )
    return render(request, "projects/project_archive.html", {"projects": projects})


@login_required
def project_detail(request: HttpRequest, project_id) -> HttpResponse:
    """Affiche un projet et ses macro-activités accessibles au propriétaire."""
    project = get_object_or_404(
        get_projects_for_user(user=request.user, include_archived=True), pk=project_id
    )
    return render(request, "projects/project_detail.html", {"project": project})


@login_required
def project_create(request: HttpRequest) -> HttpResponse:
    """Crée un projet en attribuant le propriétaire depuis la session."""
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        messages.success(request, "Le projet a été créé.")
        return redirect("projects:detail", project_id=project.id)
    return render(request, "projects/project_form.html", {"form": form})


@login_required
def project_update(request: HttpRequest, project_id) -> HttpResponse:
    """Modifie un projet appartenant exclusivement à l'utilisateur connecté."""
    project = get_object_or_404(
        get_projects_for_user(user=request.user, include_archived=True), pk=project_id
    )
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le projet a été mis à jour.")
        return redirect("projects:detail", project_id=project.id)
    return render(
        request, "projects/project_form.html", {"form": form, "project": project}
    )


@require_POST
@login_required
def project_archive(request: HttpRequest, project_id) -> HttpResponse:
    """Archive un projet appartenant à l'utilisateur connecté."""
    project = get_object_or_404(get_projects_for_user(user=request.user), pk=project_id)
    archive_project(project=project)
    messages.success(request, "Le projet a été archivé.")
    return redirect("projects:list")


@require_POST
@login_required
def project_reactivate(request: HttpRequest, project_id) -> HttpResponse:
    """Réactive un projet archivé appartenant à l'utilisateur connecté."""
    project = get_object_or_404(
        get_projects_for_user(user=request.user, include_archived=True),
        pk=project_id,
        status=Project.Status.ARCHIVED,
    )
    reactivate_project(project=project)
    messages.success(request, "Le projet a été réactivé.")
    return redirect("projects:detail", project_id=project.id)


@login_required
def project_delete(request: HttpRequest, project_id) -> HttpResponse:
    """Affiche la confirmation ou supprime définitivement un projet en POST."""
    project = get_object_or_404(
        get_projects_for_user(user=request.user, include_archived=True), pk=project_id
    )
    if request.method == "POST":
        project.delete()
        messages.success(request, "Le projet a été supprimé.")
        return redirect("projects:list")
    return render(request, "projects/project_confirm_delete.html", {"project": project})


@login_required
def macro_activity_create(request: HttpRequest, project_id) -> HttpResponse:
    """Ajoute une macro-activité à un projet appartenant à l'utilisateur."""
    project = get_object_or_404(get_projects_for_user(user=request.user), pk=project_id)
    form = MacroActivityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False)
        activity.project = project
        activity.save()
        messages.success(request, "La macro-activité a été ajoutée.")
        return redirect("projects:detail", project_id=project.id)
    return render(
        request,
        "projects/macro_activity_form.html",
        {"form": form, "project": project},
    )


@login_required
def macro_activity_update(request: HttpRequest, activity_id) -> HttpResponse:
    """Modifie une macro-activité visible par l'utilisateur connecté."""
    activity = get_object_or_404(
        get_macro_activities_for_user(user=request.user), pk=activity_id
    )
    form = MacroActivityForm(request.POST or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La macro-activité a été mise à jour.")
        return redirect("projects:detail", project_id=activity.project_id)
    return render(
        request,
        "projects/macro_activity_form.html",
        {"form": form, "project": activity.project, "activity": activity},
    )


@require_POST
@login_required
def macro_activity_delete(request: HttpRequest, activity_id) -> HttpResponse:
    """Supprime en POST une macro-activité accessible à l'utilisateur."""
    activity = get_object_or_404(
        get_macro_activities_for_user(user=request.user), pk=activity_id
    )
    project_id = activity.project_id
    activity.delete()
    messages.success(request, "La macro-activité a été supprimée.")
    return redirect("projects:detail", project_id=project_id)
