"""Formulaires de création, modification et report des tâches."""

from django import forms

from apps.accounts.models import User
from apps.projects.forms import DateInput
from apps.projects.models import MacroActivity, Project

from .models import Task


class TaskForm(forms.ModelForm):
    """Édite une tâche avec des relations limitées à l'utilisateur courant."""

    class Meta:
        """Configure les champs métier accessibles dans la fiche d'une tâche."""

        model = Task
        fields = (
            "project",
            "macro_activity",
            "title",
            "description",
            "status",
            "priority",
            "start_date",
            "planned_date",
            "deadline",
            "estimated_load",
            "origin",
            "waiting_for",
            "waiting_comment",
        )
        widgets = {
            "start_date": DateInput(),
            "planned_date": DateInput(),
            "deadline": DateInput(),
        }

    def __init__(self, *args, user: User, **kwargs):
        """Limite les projets et macro-activités aux données du propriétaire."""
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["project"].queryset = Project.objects.filter(owner=user).exclude(
            status=Project.Status.ARCHIVED
        )
        self.fields["macro_activity"].queryset = MacroActivity.objects.filter(
            project__owner=user
        ).exclude(project__status=Project.Status.ARCHIVED)

    def clean(self):
        """Vérifie que l'activité sélectionnée appartient au projet choisi."""
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        activity = cleaned_data.get("macro_activity")
        if activity and project and activity.project_id != project.id:
            self.add_error(
                "macro_activity",
                "La macro-activité doit appartenir au projet sélectionné.",
            )
        return cleaned_data


class TaskDateForm(forms.Form):
    """Valide une date transmise par une action rapide."""

    date = forms.DateField(label="Date", widget=DateInput())
