from django.urls import path

from . import views

urlpatterns = [
    path("<int:status_code>", views.custom_response, name="custom-response"),
]
