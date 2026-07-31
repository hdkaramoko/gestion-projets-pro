"""Formulaires de capture et de transformation en tâche."""

from django import forms

from apps.accounts.models import User
from apps.projects.forms import DateInput
from apps.projects.models import MacroActivity, Project

from .models import InboxItem


class InboxItemForm(forms.ModelForm):
    """Capture un élément avec un unique champ pour rester immédiat."""

    class Meta:
        """Expose seulement le contenu saisi rapidement."""

        model = InboxItem
        fields = ("content",)
        widgets = {
            "content": forms.TextInput(
                attrs={"placeholder": "Une idée, une action, un rappel…"}
            )
        }


class InboxConversionForm(forms.Form):
    """Collecte les informations nécessaires à la création d'une tâche."""

    project = forms.ModelChoiceField(label="Projet", queryset=Project.objects.none())
    macro_activity = forms.ModelChoiceField(
        label="Macro-activité",
        queryset=MacroActivity.objects.none(),
        required=False,
    )
    priority = forms.ChoiceField(
        label="Priorité",
        choices=Project.Priority.choices,
        initial=Project.Priority.NORMAL,
    )
    planned_date = forms.DateField(
        label="Date planifiée", required=False, widget=DateInput()
    )
    deadline = forms.DateField(label="Échéance", required=False, widget=DateInput())

    def __init__(self, *args, user: User, **kwargs):
        """Limite les relations proposées aux données actives de l'utilisateur."""
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(owner=user).exclude(
            status=Project.Status.ARCHIVED
        )
        self.fields["macro_activity"].queryset = MacroActivity.objects.filter(
            project__owner=user
        ).exclude(project__status=Project.Status.ARCHIVED)

    def clean(self):
        """Garantit que la macro-activité appartient au projet sélectionné."""
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        activity = cleaned_data.get("macro_activity")
        if project and activity and activity.project_id != project.id:
            self.add_error(
                "macro_activity",
                "La macro-activité doit appartenir au projet sélectionné.",
            )
        return cleaned_data
