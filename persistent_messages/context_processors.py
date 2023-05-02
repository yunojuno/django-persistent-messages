from typing import Callable

from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from .shortcuts import get_all_messages, get_persistent_messages
from .templatetags.persistent_message_tags import serialize_messages


def persistent_messages(request: HttpRequest) -> dict[str, Callable[[], list[Message]]]:
    """Return just the persistent messages."""
    return {"persistent_messages": lambda: get_persistent_messages(request)}


def all_messages(request: HttpRequest) -> dict[str, Callable[[], list[Message]]]:
    """Return contrib.messages and persistent_messages combined (and serialized)."""
    return {"all_messages": lambda: serialize_messages(get_all_messages(request))}
