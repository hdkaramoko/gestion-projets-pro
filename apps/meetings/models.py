"""Modèles des réunions et des actions qui en découlent."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.projects.models import Project
from apps.tasks.models import Task


class Meeting(models.Model):
    """Compte rendu d'une réunion rattachée à un projet personnel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetings",
        verbose_name="propriétaire",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="meetings",
        verbose_name="projet",
    )
    title = models.CharField("titre", max_length=200)
    scheduled_at = models.DateTimeField("date et heure")
    participants = models.TextField("participants", blank=True)
    context = models.TextField("contexte", blank=True)
    discussion_points = models.TextField("points discutés", blank=True)
    decisions = models.TextField("décisions prises", blank=True)
    next_steps = models.TextField("prochaines étapes", blank=True)
    notes = models.TextField("notes complémentaires", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        """Trie les réunions de la plus récente à la plus ancienne."""

        ordering = ("-scheduled_at",)
        verbose_name = "réunion"
        verbose_name_plural = "réunions"

    def __str__(self) -> str:
        """Retourne le titre et la date de la réunion."""
        return f"{self.title} — {self.scheduled_at:%d/%m/%Y}"

    def clean(self) -> None:
        """Garantit que le projet appartient au propriétaire de la réunion."""
        super().clean()
        if self.owner_id and self.project_id and self.owner_id != self.project.owner_id:
            raise ValidationError(
                {"project": "Ce projet n'appartient pas au propriétaire choisi."}
            )


class MeetingAction(models.Model):
    """Action décidée pendant une réunion et convertible en tâche."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="réunion",
    )
    title = models.CharField("intitulé", max_length=200)
    description = models.TextField("description", blank=True)
    assignee = models.CharField("responsable", max_length=200, blank=True)
    deadline = models.DateField("échéance", blank=True, null=True)
    priority = models.CharField(
        "priorité",
        max_length=20,
        choices=Project.Priority.choices,
        default=Project.Priority.NORMAL,
    )
    created_task = models.OneToOneField(
        Task,
        on_delete=models.SET_NULL,
        related_name="source_meeting_action",
        verbose_name="tâche créée",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        """Conserve l'ordre de saisie des actions de réunion."""

        ordering = ("created_at",)
        verbose_name = "action de réunion"
        verbose_name_plural = "actions de réunion"

    def __str__(self) -> str:
        """Retourne l'intitulé de l'action."""
        return self.title

    def clean(self) -> None:
        """Vérifie la cohérence d'une éventuelle tâche déjà créée."""
        super().clean()
        if self.created_task_id and (
            self.created_task.project_id != self.meeting.project_id
            or self.created_task.owner_id != self.meeting.owner_id
        ):
            raise ValidationError(
                {"created_task": "La tâche doit reprendre le projet de la réunion."}
            )
