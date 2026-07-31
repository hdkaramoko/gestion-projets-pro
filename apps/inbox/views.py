"""Vues sécurisées de capture et de qualification."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import InboxConversionForm, InboxItemForm
from .models import InboxItem
from .selectors import get_inbox_items_for_user
from .services import convert_inbox_item_to_task, set_inbox_item_status


@login_required
def inbox_list(request: HttpRequest) -> HttpResponse:
    """Affiche les captures non archivées et permet un ajout immédiat."""
    form = InboxItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        messages.success(request, "L'élément a été ajouté à la boîte de réception.")
        return redirect("inbox:list")

    items = get_inbox_items_for_user(user=request.user)
    status = request.GET.get("status", "")
    if status in InboxItem.Status.values and status != InboxItem.Status.ARCHIVED:
        items = items.filter(status=status)
    return render(
        request,
        "inbox/inbox_list.html",
        {"form": form, "items": items, "selected_status": status},
    )


@login_required
def inbox_archive_list(request: HttpRequest) -> HttpResponse:
    """Affiche les éléments archivés appartenant à l'utilisateur."""
    items = get_inbox_items_for_user(user=request.user, include_archived=True).filter(
        status=InboxItem.Status.ARCHIVED
    )
    return render(request, "inbox/inbox_archive.html", {"items": items})


@login_required
def inbox_convert(request: HttpRequest, item_id) -> HttpResponse:
    """Qualifie une capture et la transforme en tâche une seule fois."""
    item = get_object_or_404(get_inbox_items_for_user(user=request.user), pk=item_id)
    if item.status != InboxItem.Status.TO_PROCESS:
        messages.error(request, "Cet élément ne peut plus être transformé.")
        return redirect("inbox:list")

    form = InboxConversionForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            task = convert_inbox_item_to_task(
                item=item,
                project=form.cleaned_data["project"],
                macro_activity=form.cleaned_data["macro_activity"],
                priority=form.cleaned_data["priority"],
                planned_date=form.cleaned_data["planned_date"],
                deadline=form.cleaned_data["deadline"],
            )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("inbox:list")
        messages.success(request, "L'élément a été transformé en tâche.")
        return redirect("tasks:detail", task_id=task.id)
    return render(
        request,
        "inbox/inbox_convert.html",
        {"form": form, "item": item},
    )


@require_POST
@login_required
def inbox_ignore(request: HttpRequest, item_id) -> HttpResponse:
    """Marque comme ignorée une capture appartenant à l'utilisateur."""
    item = get_object_or_404(
        get_inbox_items_for_user(user=request.user),
        pk=item_id,
        status=InboxItem.Status.TO_PROCESS,
    )
    set_inbox_item_status(item=item, status=InboxItem.Status.IGNORED)
    messages.success(request, "L'élément a été ignoré.")
    return redirect("inbox:list")


@require_POST
@login_required
def inbox_archive(request: HttpRequest, item_id) -> HttpResponse:
    """Archive une capture traitée ou non appartenant à l'utilisateur."""
    item = get_object_or_404(get_inbox_items_for_user(user=request.user), pk=item_id)
    set_inbox_item_status(item=item, status=InboxItem.Status.ARCHIVED)
    messages.success(request, "L'élément a été archivé.")
    return redirect("inbox:list")


@require_POST
@login_required
def inbox_delete(request: HttpRequest, item_id) -> HttpResponse:
    """Supprime définitivement en POST une capture accessible."""
    item = get_object_or_404(
        get_inbox_items_for_user(user=request.user, include_archived=True),
        pk=item_id,
    )
    item.delete()
    messages.success(request, "L'élément a été supprimé.")
    return redirect("inbox:list")
