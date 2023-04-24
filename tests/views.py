from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def custom_response(request: HttpRequest, status_code: int) -> HttpResponse:
    return render(request, "custom_response.html", {"status_code": status_code})
