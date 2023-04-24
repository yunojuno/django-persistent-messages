from django.http import HttpRequest

from .models import get_user_messages


def persistent_messages(request: HttpRequest) -> dict[str, list[dict[str, str]]]:
    """Add persistent messages to the request context."""
    return {
        "persistent_messages": [
            {
                "level": pm.level,
                "level_tag": pm.level_tag,
                "message": pm.message,
                "extra_tags": pm.extra_tags,
            }
            for pm in get_user_messages(request.user)
        ]
    }
