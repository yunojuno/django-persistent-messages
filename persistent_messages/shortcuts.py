from __future__ import annotations

from django.contrib.messages import get_messages
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from .models import PersistentMessage


def get_persistent_messages(request: HttpRequest) -> list[Message]:
    """Return the persistent messages for the given user."""
    return [
        m.as_django_message()
        for m in PersistentMessage.objects.filter_user(request.user).active()
        # order by most important first (CRITICAL -> DEBUG)
        .order_by("-level", "-created_at")
    ]


def get_all_messages(request: HttpRequest) -> dict[str, list[Message]]:
    """Return flash messages and persistent messages for the given user."""
    return {
        "messages": list(get_messages(request)) + get_persistent_messages(request.user)
    }
