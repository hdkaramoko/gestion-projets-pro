"""Services métier des actions issues de réunion."""

from django.db import transaction

from apps.tasks.models import Task

from .models import MeetingAction


@transaction.atomic
def convert_meeting_action_to_task(*, action: MeetingAction) -> Task:
    """Transforme une action de réunion en une unique tâche.

    La ligne est verrouillée pendant la conversion afin d'empêcher deux
    créations concurrentes pour la même action.

    Raises:
        ValueError: Si une tâche existe déjà pour cette action.
    """
    locked_action = (
        MeetingAction.objects.select_for_update()
        .select_related("meeting", "meeting__project")
        .get(pk=action.pk)
    )
    if locked_action.created_task_id:
        raise ValueError("Cette action a déjà été transformée en tâche.")
    task = Task(
        owner=locked_action.meeting.owner,
        project=locked_action.meeting.project,
        title=locked_action.title,
        description=locked_action.description,
        deadline=locked_action.deadline,
        priority=locked_action.priority,
        origin=Task.Origin.MEETING,
    )
    task.full_clean()
    task.save()
    locked_action.created_task = task
    locked_action.save(update_fields=("created_task",))
    return task
