import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from persistent_messages.models import PersistentMessage


@pytest.mark.django_db
class TestMiddleware:
    def assert_message(self, response, message):
        assert message in [m.message for m in response.context["messages"]]

    def assert_no_message(self, response, message):
        assert message not in [m.message for m in response.context["messages"]]

    def test_message_added(
        self, pm: PersistentMessage, user: User, client: Client
    ) -> None:
        client.force_login(user)
        response = client.get(reverse("custom-response", kwargs={"status_code": 200}))
        self.assert_message(response, pm.message)

    def test_message_not_added(self, pm: PersistentMessage, client: Client) -> None:
        response = client.get(reverse("custom-response", kwargs={"status_code": 200}))
        self.assert_no_message(response, pm.message)
