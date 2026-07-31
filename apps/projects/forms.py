"""Formulaires des projets et macro-activités."""

from django import forms

from .models import MacroActivity, Project


class DateInput(forms.DateInput):
    """Champ de date utilisant le sélecteur natif du navigateur."""

    input_type = "date"


class ProjectForm(forms.ModelForm):
    """Crée ou modifie un projet sans exposer son propriétaire."""

    class Meta:
        """Configure les champs métier éditables d'un projet."""

        model = Project
        fields = (
            "name",
            "description",
            "status",
            "priority",
            "start_date",
            "deadline",
            "color",
            "estimated_load",
            "notes",
        )
        widgets = {
            "start_date": DateInput(),
            "deadline": DateInput(),
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class MacroActivityForm(forms.ModelForm):
    """Crée ou modifie une macro-activité dans un projet imposé par la vue."""

    class Meta:
        """Configure les champs éditables d'une macro-activité."""

        model = MacroActivity
        fields = (
            "title",
            "description",
            "status",
            "priority",
            "start_date",
            "deadline",
            "display_order",
        )
        widgets = {"start_date": DateInput(), "deadline": DateInput()}
