from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from .models import get_user_messages


def get_messages(request: HttpRequest) -> list[str]:
    return [m for m in messages.get_messages(request)]


class PersistentMessageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Only add messages if the response is successful.
        if 200 <= response.status_code < 300:
            self.add_messages(request)
        return response

    def add_messages(self, request: HttpRequest) -> None:
        existing_messages = get_messages(request)
        for message in get_user_messages(request.user):
            # ignore duplicate messages
            if message.message in existing_messages:
                continue
            messages.add_message(
                request,
                message.level,
                message.message,
                message.extra_tags,
            )
