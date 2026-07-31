"""Modèles des projets et des macro-activités."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Project(models.Model):
    """Projet personnel regroupant les activités suivies par un utilisateur."""

    class Status(models.TextChoices):
        """Statuts possibles du cycle de vie d'un projet."""

        UPCOMING = "upcoming", "À venir"
        ACTIVE = "active", "Actif"
        PAUSED = "paused", "En pause"
        COMPLETED = "completed", "Terminé"
        ARCHIVED = "archived", "Archivé"

    class Priority(models.TextChoices):
        """Niveaux de priorité applicables à un projet."""

        LOW = "low", "Basse"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Haute"
        CRITICAL = "critical", "Critique"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="propriétaire",
    )
    name = models.CharField("nom", max_length=200)
    description = models.TextField("description", blank=True)
    status = models.CharField(
        "statut", max_length=20, choices=Status.choices, default=Status.UPCOMING
    )
    priority = models.CharField(
        "priorité",
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    start_date = models.DateField("date de début", blank=True, null=True)
    deadline = models.DateField("échéance", blank=True, null=True)
    color = models.CharField("couleur", max_length=7, default="#315efb")
    estimated_load = models.PositiveIntegerField(
        "charge estimée en minutes", blank=True, null=True
    )
    notes = models.TextField("contexte ou notes générales", blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)
    archived_at = models.DateTimeField("archivé le", blank=True, null=True)

    class Meta:
        """Définit le tri et la cohérence des dates des projets."""

        ordering = ("-priority", "deadline", "name")
        verbose_name = "projet"
        verbose_name_plural = "projets"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(deadline__isnull=True)
                    | Q(deadline__gte=models.F("start_date"))
                ),
                name="project_deadline_after_start",
            )
        ]

    def __str__(self) -> str:
        """Retourne le nom du projet."""
        return self.name

    def clean(self) -> None:
        """Valide que l'échéance n'est pas antérieure au début du projet."""
        super().clean()
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError(
                {"deadline": "L'échéance ne peut pas précéder la date de début."}
            )

    @property
    def progress(self) -> int:
        """Calcule la progression à partir des tâches ou des macro-activités.

        Les tâches priment dès que le projet en possède. Les éléments abandonnés
        sont exclus du calcul.
        """
        tasks = self.tasks.exclude(status="cancelled")
        task_count = tasks.count()
        if task_count:
            completed_tasks = tasks.filter(status="completed").count()
            return round(completed_tasks * 100 / task_count)
        activities = self.macro_activities.exclude(
            status=MacroActivity.Status.CANCELLED
        )
        total = activities.count()
        if not total:
            return 0
        completed = activities.filter(status=MacroActivity.Status.COMPLETED).count()
        return round(completed * 100 / total)


class MacroActivity(models.Model):
    """Lot de travail structurant appartenant à un projet."""

    class Status(models.TextChoices):
        """Statuts de suivi d'une macro-activité."""

        TODO = "todo", "À faire"
        IN_PROGRESS = "in_progress", "En cours"
        WAITING = "waiting", "En attente"
        COMPLETED = "completed", "Terminée"
        CANCELLED = "cancelled", "Abandonnée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="macro_activities",
        verbose_name="projet",
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
        blank=True,
    )
    start_date = models.DateField("date de début", blank=True, null=True)
    deadline = models.DateField("échéance", blank=True, null=True)
    display_order = models.PositiveIntegerField("ordre d'affichage", default=0)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        """Définit le tri et la cohérence des dates des macro-activités."""

        ordering = ("display_order", "created_at")
        verbose_name = "macro-activité"
        verbose_name_plural = "macro-activités"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(deadline__isnull=True)
                    | Q(deadline__gte=models.F("start_date"))
                ),
                name="macro_activity_deadline_after_start",
            )
        ]

    def __str__(self) -> str:
        """Retourne le titre accompagné du projet."""
        return f"{self.title} — {self.project.name}"

    def clean(self) -> None:
        """Valide que l'échéance ne précède pas le début de l'activité."""
        super().clean()
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError(
                {"deadline": "L'échéance ne peut pas précéder la date de début."}
            )

    @property
    def is_actionable(self) -> bool:
        """Indique si la macro-activité constitue elle-même une action.

        Une activité ouverte est actionnable lorsqu'elle ne contient aucune
        tâche active. Les tâches terminées ou abandonnées ne la masquent pas.
        """
        if self.status in {self.Status.COMPLETED, self.Status.CANCELLED}:
            return False
        if not self.pk:
            return True
        return not self.tasks.exclude(status__in=("completed", "cancelled")).exists()
