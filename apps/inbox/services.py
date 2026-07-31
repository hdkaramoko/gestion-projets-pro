"""Services métier de traitement de la boîte de réception."""

from django.db import transaction
from django.utils import timezone

from apps.projects.models import MacroActivity, Project
from apps.tasks.models import Task

from .models import InboxItem


@transaction.atomic
def convert_inbox_item_to_task(
    *,
    item: InboxItem,
    project: Project,
    macro_activity: MacroActivity | None,
    priority: str,
    planned_date,
    deadline,
) -> Task:
    """Transforme une capture en une unique tâche de manière atomique.

    L'élément est verrouillé pendant l'opération afin que deux requêtes
    simultanées ne puissent pas créer deux tâches.

    Raises:
        ValueError: Si l'élément est déjà converti ou si les relations ne sont
            pas cohérentes avec son propriétaire.
    """
    locked_item = InboxItem.objects.select_for_update().get(pk=item.pk)
    if locked_item.status != InboxItem.Status.TO_PROCESS:
        raise ValueError("Seul un élément à qualifier peut être transformé.")
    if locked_item.converted_task_id:
        raise ValueError("Cet élément a déjà été transformé en tâche.")
    if project.owner_id != locked_item.owner_id:
        raise ValueError("Le projet n'appartient pas au propriétaire de l'élément.")
    if macro_activity and macro_activity.project_id != project.id:
        raise ValueError("La macro-activité n'appartient pas au projet.")

    task = Task(
        owner=locked_item.owner,
        project=project,
        macro_activity=macro_activity,
        title=locked_item.content,
        priority=priority,
        planned_date=planned_date,
        deadline=deadline,
        origin=Task.Origin.INBOX,
    )
    task.full_clean()
    task.save()
    locked_item.status = InboxItem.Status.CONVERTED
    locked_item.processed_at = timezone.now()
    locked_item.converted_task = task
    locked_item.save(update_fields=("status", "processed_at", "converted_task"))
    return task


def set_inbox_item_status(*, item: InboxItem, status: str) -> InboxItem:
    """Marque une capture comme ignorée ou archivée avec sa date de traitement."""
    if status not in {InboxItem.Status.IGNORED, InboxItem.Status.ARCHIVED}:
        raise ValueError("Ce statut de traitement n'est pas autorisé.")
    item.status = status
    item.processed_at = timezone.now()
    item.save(update_fields=("status", "processed_at"))
    return item
