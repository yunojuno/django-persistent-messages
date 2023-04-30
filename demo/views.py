from django.contrib.messages import add_message
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    add_message(request, 20, "Hello, world!")
    return render(request, "index.html")
