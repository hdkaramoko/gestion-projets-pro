"""Services métier réalisant les actions rapides sur les tâches."""

from datetime import date

from .models import Task


def change_task_status(*, task: Task, status: str) -> Task:
    """Modifie le statut d'une tâche et synchronise sa réalisation.

    Args:
        task: Tâche appartenant à l'utilisateur à l'origine de l'action.
        status: Nouveau statut parmi les valeurs autorisées.

    Returns:
        Tâche enregistrée avec sa date de réalisation cohérente.

    Raises:
        ValueError: Si le statut demandé n'est pas reconnu.
    """
    if status not in Task.Status.values:
        raise ValueError("Statut de tâche invalide.")
    task.status = status
    task.save(update_fields=("status", "completed_at", "updated_at"))
    return task


def reschedule_task(*, task: Task, planned_date: date) -> Task:
    """Reporte la date planifiée sans modifier l'échéance de la tâche."""
    task.planned_date = planned_date
    task.save(update_fields=("planned_date", "updated_at"))
    return task


def change_task_deadline(*, task: Task, deadline: date) -> Task:
    """Modifie l'échéance sans toucher à la date de travail planifiée."""
    task.deadline = deadline
    task.save(update_fields=("deadline", "updated_at"))
    return task
