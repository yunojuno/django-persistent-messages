from django.urls import path

from . import views

app_name = "persistent_messages"

urlpatterns = [
    path("dismiss/<int:message_id>/", views.dismiss_message, name="dismiss_message"),
]
