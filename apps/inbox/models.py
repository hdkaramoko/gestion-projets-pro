"""Modèle des éléments capturés dans la boîte de réception."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.tasks.models import Task


class InboxItem(models.Model):
    """Idée ou action capturée rapidement avant sa qualification."""

    class Status(models.TextChoices):
        """États possibles du traitement d'un élément capturé."""

        TO_PROCESS = "to_process", "À qualifier"
        CONVERTED = "converted", "Transformé en tâche"
        IGNORED = "ignored", "Ignoré"
        ARCHIVED = "archived", "Archivé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inbox_items",
        verbose_name="propriétaire",
    )
    content = models.CharField("titre ou contenu", max_length=200)
    status = models.CharField(
        "statut",
        max_length=20,
        choices=Status.choices,
        default=Status.TO_PROCESS,
    )
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    processed_at = models.DateTimeField("traité le", blank=True, null=True)
    converted_task = models.OneToOneField(
        Task,
        on_delete=models.SET_NULL,
        related_name="source_inbox_item",
        verbose_name="tâche créée",
        blank=True,
        null=True,
    )

    class Meta:
        """Présente en priorité les captures les plus récentes."""

        ordering = ("-created_at",)
        verbose_name = "élément de boîte de réception"
        verbose_name_plural = "éléments de boîte de réception"

    def __str__(self) -> str:
        """Retourne le contenu court de l'élément."""
        return self.content

    def clean(self) -> None:
        """Vérifie que la tâche liée appartient au même utilisateur."""
        super().clean()
        if (
            self.converted_task_id
            and self.owner_id
            and self.converted_task.owner_id != self.owner_id
        ):
            raise ValidationError(
                {"converted_task": "La tâche doit appartenir au même utilisateur."}
            )
