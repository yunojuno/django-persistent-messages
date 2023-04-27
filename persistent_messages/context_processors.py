from django.http import HttpRequest

from .models import get_user_messages


def persistent_messages(request: HttpRequest) -> dict[str, list[dict[str, str]]]:
    """Add persistent messages to the request context."""
    messages = {
        "persistent_messages": [
            {
                "pk": pm.pk,
                "level": pm.level,
                "status": pm.level_tag,
                "message": pm.message,
                "extra_tags": pm.extra_tags,
                "is_dismissable": pm.is_dismissable,
                "is_safe": pm.mark_content_safe,
            }
            for pm in get_user_messages(request.user)
        ]
    }
    return messages
