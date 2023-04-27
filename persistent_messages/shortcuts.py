from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http import HttpRequest

from .models import PersistentMessage


def get_request_messages(request: HttpRequest) -> list[str]:
    """Return the list of existing messages as strings."""
    return [str(m) for m in messages.get_messages(request)]


def is_duplicate(request: HttpRequest, message: str) -> bool:
    """Return True if the message is already in the message store."""
    return message in get_request_messages(request)


def add_message(request: HttpRequest, persistent_message: PersistentMessage) -> None:
    """Add a message to the message store."""
    if is_duplicate(request, persistent_message.message):
        return
    messages.add_message(
        request,
        persistent_message.level,
        persistent_message.message,
        persistent_message.extra_tags,
    )


def get_user_messages(
    user: settings.AUTH_USER_MODEL | AnonymousUser,
) -> models.QuerySet[PersistentMessage]:
    """
    Return the messages for the given user.

    If the user is not authenticated, only messages targeted at all users
    will be returned.

    """
    return PersistentMessage.objects.filter_user(user).active()
