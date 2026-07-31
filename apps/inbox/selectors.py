"""Sélecteurs sécurisés de la boîte de réception."""

from django.db.models import QuerySet

from apps.accounts.models import User

from .models import InboxItem


def get_inbox_items_for_user(
    *, user: User, include_archived: bool = False
) -> QuerySet[InboxItem]:
    """Retourne uniquement les captures appartenant à l'utilisateur."""
    items = InboxItem.objects.filter(owner=user).select_related("converted_task")
    if not include_archived:
        items = items.exclude(status=InboxItem.Status.ARCHIVED)
    return items
