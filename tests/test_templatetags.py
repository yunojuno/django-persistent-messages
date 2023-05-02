from django.contrib.messages.storage.base import Message

from persistent_messages.models import PersistentMessage
from persistent_messages.templatetags.persistent_message_tags import sort_messages


class TestSortMessages:
    def test_sort(self) -> None:
        pm = PersistentMessage(level=10, content="a")
        msg = Message(level=20, message="c")
        obj = {"level": 30, "message": "b"}
        assert sort_messages([pm, msg, obj], "level") == [pm, msg, obj]
        assert sort_messages([pm, msg, obj], "-level") == [obj, msg, pm]
        assert sort_messages([pm, msg, obj], "message") == [pm, obj, msg]
        assert sort_messages([pm, msg, obj], "-message") == [msg, obj, pm]
