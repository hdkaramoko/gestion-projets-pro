"""Formulaires des réunions et de leurs actions."""

from django import forms

from apps.accounts.models import User
from apps.projects.forms import DateInput
from apps.projects.models import Project

from .models import Meeting, MeetingAction


class DateTimeInput(forms.DateTimeInput):
    """Champ de date et heure utilisant le contrôle natif du navigateur."""

    input_type = "datetime-local"


class MeetingForm(forms.ModelForm):
    """Édite un compte rendu avec les seuls projets de l'utilisateur."""

    class Meta:
        """Configure les champs éditables d'une réunion."""

        model = Meeting
        fields = (
            "project",
            "title",
            "scheduled_at",
            "participants",
            "context",
            "discussion_points",
            "decisions",
            "next_steps",
            "notes",
        )
        widgets = {
            "scheduled_at": DateTimeInput(format="%Y-%m-%dT%H:%M"),
            "participants": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user: User, **kwargs):
        """Limite le projet aux projets non archivés de l'utilisateur."""
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(owner=user).exclude(
            status=Project.Status.ARCHIVED
        )
        self.fields["scheduled_at"].input_formats = ("%Y-%m-%dT%H:%M",)


class MeetingActionForm(forms.ModelForm):
    """Ajoute ou modifie une action dans une réunion imposée par la vue."""

    class Meta:
        """Configure les informations éditables d'une action décidée."""

        model = MeetingAction
        fields = ("title", "description", "assignee", "deadline", "priority")
        widgets = {"deadline": DateInput()}
