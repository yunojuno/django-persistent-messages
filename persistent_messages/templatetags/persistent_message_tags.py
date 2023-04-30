import logging
from datetime import datetime
from typing import Iterable

from django import template
from django.conf import settings
from django.contrib.messages.storage.base import Message

from persistent_messages.models import PersistentMessage

register = template.Library()
logger = logging.getLogger(__name__)


def _serialize_message(message: Message) -> dict:
    tags = message.tags.split()
    return {
        "pk": "",
        "level": message.level,
        "level_tag": message.level_tag,
        "message": message.message,
        "extra_tags": message.extra_tags,
        "tags": message.tags,
        "is_safe": "safe" in tags,
        "is_dismissable": "dismissable" in tags,
        "is_persistent": False,
        "dismiss_url": "",
    }


def _serialize_persistent_message(message: PersistentMessage) -> dict:
    return {
        "pk": message.pk,
        "level": message.level,
        "level_tag": message.level_tag,
        "message": message.message,
        "extra_tags": message.extra_tags,
        "tags": message.tags,
        "is_safe": message.mark_content_safe,
        "is_dismissable": message.is_dismissable,
        "is_persistent": True,
        "dismiss_url": message.dismiss_url(),
    }


@register.filter("serialize_message")
def serialize_message(message: PersistentMessage | Message) -> dict:
    if isinstance(message, PersistentMessage):
        return _serialize_persistent_message(message)
    elif isinstance(message, Message):
        return _serialize_message(message)
    else:
        raise ValueError(f"Unknown message type {type(message)}")


@register.filter("serialize_messages")
def serialize_messages(messages: Iterable[PersistentMessage | Message]) -> list[dict]:
    return [serialize_message(m) for m in messages]


@register.filter("sort_messages")
def sort_messages(
    messages: Iterable[PersistentMessage | Message], sort_by: str = "level"
) -> list[Message]:
    sort_by = sort_by or "level"
    reverse = sort_by.startswith("-")

    def key(message: PersistentMessage | Message) -> str | int | datetime:
        return getattr(message, sort_by.lstrip("-"))

    try:
        return sorted(
            messages,
            key=key,
            reverse=reverse,
        )
    except Exception as ex:
        if settings.DEBUG:
            raise Exception(f"Error sorting messages: {ex}") from ex
        logger.warning("Error sorting messages - returning unsorted")
        return list(messages)
