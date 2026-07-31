"""Modèle et règles métier des tâches."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.projects.models import MacroActivity, Project


class Task(models.Model):
    """Action opérationnelle appartenant à un projet et à un utilisateur."""

    class Status(models.TextChoices):
        """États possibles du cycle de vie d'une tâche."""

        TODO = "todo", "À faire"
        IN_PROGRESS = "in_progress", "En cours"
        WAITING = "waiting", "En attente"
        COMPLETED = "completed", "Terminée"
        CANCELLED = "cancelled", "Abandonnée"

    class Origin(models.TextChoices):
        """Sources possibles de création d'une tâche."""

        MANUAL = "manual", "Saisie manuelle"
        INBOX = "inbox", "Boîte de réception"
        MEETING = "meeting", "Réunion"
        OTHER = "other", "Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="propriétaire",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="projet",
    )
    macro_activity = models.ForeignKey(
        MacroActivity,
        on_delete=models.SET_NULL,
        related_name="tasks",
        verbose_name="macro-activité",
        blank=True,
        null=True,
    )
    title = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        "priorité",
        max_length=20,
        choices=Project.Priority.choices,
        default=Project.Priority.NORMAL,
    )
    start_date = models.DateField("date de début", blank=True, null=True)
    planned_date = models.DateField("date planifiée", blank=True, null=True)
    deadline = models.DateField("échéance", blank=True, null=True)
    estimated_load = models.PositiveIntegerField(
        "charge estimée en minutes", blank=True, null=True
    )
    origin = models.CharField(
        "origine", max_length=20, choices=Origin.choices, default=Origin.MANUAL
    )
    waiting_for = models.CharField(
        "personne ou entité attendue", max_length=200, blank=True
    )
    waiting_comment = models.TextField("commentaire d'attente", blank=True)
    completed_at = models.DateTimeField("réalisée le", blank=True, null=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        """Définit les libellés et l'ordre de lecture des tâches."""

        ordering = ("deadline", "planned_date", "-priority", "created_at")
        verbose_name = "tâche"
        verbose_name_plural = "tâches"

    def __str__(self) -> str:
        """Retourne le titre de la tâche."""
        return self.title

    def clean(self) -> None:
        """Garantit la cohérence du propriétaire, du projet et de l'activité."""
        super().clean()
        errors = {}
        if self.project_id and self.owner_id and self.owner_id != self.project.owner_id:
            errors["project"] = "Ce projet n'appartient pas au propriétaire choisi."
        if (
            self.macro_activity_id
            and self.project_id
            and self.macro_activity.project_id != self.project_id
        ):
            errors["macro_activity"] = (
                "La macro-activité doit appartenir au même projet que la tâche."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        """Synchronise la date de réalisation avec le statut avant sauvegarde."""
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != self.Status.COMPLETED:
            self.completed_at = None
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"completed_at"}
        super().save(*args, **kwargs)

    @property
    def is_overdue(self) -> bool:
        """Indique si l'échéance est dépassée pour une tâche encore active."""
        return bool(
            self.deadline
            and self.deadline < timezone.localdate()
            and self.status not in {self.Status.COMPLETED, self.Status.CANCELLED}
        )
