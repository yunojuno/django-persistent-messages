from __future__ import annotations

from functools import cache

from django.contrib.messages import get_messages
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from .models import PersistentMessage


@cache
def get_persistent_messages(request: HttpRequest) -> list[PersistentMessage]:
    """Return the persistent messages for the given user."""
    return list(
        PersistentMessage.objects.filter_user(request.user).active()
        # order by most important first (CRITICAL -> DEBUG)
        .order_by("-level", "-created_at")
    )


@cache
def get_all_messages(request: HttpRequest) -> list[PersistentMessage | Message]:
    """Return flash messages and persistent messages for the given user."""
    return list(get_messages(request)) + get_persistent_messages(request)
