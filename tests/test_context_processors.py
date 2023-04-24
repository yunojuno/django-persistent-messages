import pytest

from persistent_messages.context_processors import persistent_messages
from persistent_messages.models import PersistentMessage


@pytest.mark.django_db
class TestContextProcessors:
    def assert_message(self, response, message):
        assert message in [m.message for m in response.context["messages"]]

    def assert_no_message(self, response, message):
        assert message not in [m.message for m in response.context["messages"]]

    def test_persistent_messages(self, rf, user, pm: PersistentMessage) -> None:
        request = rf.get("/")
        request.user = user
        context = persistent_messages(request)
        assert context["persistent_messages"] == [
            {
                "level": pm.level,
                "level_tag": pm.level_tag,
                "message": pm.message,
                "extra_tags": pm.extra_tags,
            }
        ]
