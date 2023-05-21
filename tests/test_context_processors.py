import pytest

from persistent_messages.context_processors import all_messages, persistent_messages
from persistent_messages.models import PersistentMessage
from persistent_messages.templatetags.persistent_message_tags import serialize_message


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
        # context is a lambda so we need to call it to get the actual value
        assert context["persistent_messages"]() == [pm]

    def test_persistent_messages__custom_group(
        self, rf, user, pm: PersistentMessage
    ) -> None:
        request = rf.get("/")
        request.user = user
        user.first_name = "Fred"
        user.save()
        pm.target = pm.TargetType.USERS_OR_GROUPS
        pm.target_custom_group = "fred"
        pm.save()
        assert pm.user_in_custom_group(request.user)
        context = persistent_messages(request)
        # context is a lambda so we need to call it to get the actual value
        assert context["persistent_messages"]() == [pm]

    def test_all_messages(self, rf, user, pm: PersistentMessage) -> None:
        request = rf.get("/")
        request.user = user
        context = all_messages(request)
        # context is a lambda so we need to call it to get the actual value
        assert context["all_messages"]() == [serialize_message(pm)]
