from typing import Callable

from django.http import HttpRequest, HttpResponse

from .shortcuts import add_message, get_user_messages


class PersistentMessageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        for message in get_user_messages(request.user):
            add_message(request, message)
        return response
