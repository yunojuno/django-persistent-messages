from django.contrib.messages import add_message, constants
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    add_message(request, constants.INFO, "Unsafe flash message")
    add_message(request, constants.SUCCESS, "Safe flash message", extra_tags="safe")
    add_message(
        request,
        constants.WARNING,
        "Dismissable flash message",
        extra_tags="dismissable",
    )
    return render(request, "index.html")
