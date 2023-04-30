from typing import Callable

from django.contrib.messages.storage.base import Message
from django.http import HttpRequest

from .shortcuts import get_all_messages, get_persistent_messages


def persistent_messages(request: HttpRequest) -> dict[str, Callable[[], list[Message]]]:
    """Return just the persistent messages."""
    return {"persistent_messages": lambda: get_persistent_messages(request)}


def all_messages(request: HttpRequest) -> dict[str, Callable[[], list[Message]]]:
    """
    Return contrib.messages and persistent_messages combined.

    The messages are sorted by level (CRITICAL -> DEBUG).
    """
    return {"all_messages": lambda: get_all_messages(request)}
