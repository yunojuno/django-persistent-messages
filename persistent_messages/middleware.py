from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from .models import get_user_messages


class PersistentMessageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        self.add_messages(request)
        return response

    def add_messages(self, request: HttpRequest) -> None:
        for message in get_user_messages(request.user):
            messages.add_message(
                request,
                message.level,
                message.message,
                message.extra_tags,
            )
