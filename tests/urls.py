from django.urls import include, path

from . import views

urlpatterns = [
    path("<int:status_code>", views.custom_response, name="custom-response"),
    path("alerts/", include("persistent_messages.urls")),
]
