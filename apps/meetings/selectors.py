"""Sélecteurs sécurisés des réunions et actions."""

from django.db.models import QuerySet

from apps.accounts.models import User

from .models import Meeting, MeetingAction


def get_meetings_for_user(*, user: User) -> QuerySet[Meeting]:
    """Retourne les réunions appartenant à un utilisateur."""
    return Meeting.objects.filter(owner=user).select_related("project")


def get_meeting_actions_for_user(*, user: User) -> QuerySet[MeetingAction]:
    """Retourne les actions des réunions appartenant à un utilisateur."""
    return MeetingAction.objects.filter(meeting__owner=user).select_related(
        "meeting", "meeting__project", "created_task"
    )
