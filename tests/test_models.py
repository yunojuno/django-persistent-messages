import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import constants as message_constants

from persistent_messages.exceptions import UndismissableMessage
from persistent_messages.models import LEVEL_TAGS, TAG_LEVELS, PersistentMessage


def test_custom_MESSAGE_TAGS() -> None:
    # track any changes to the default tags in Django
    assert LEVEL_TAGS == {
        10: "debug",
        20: "info",
        25: "success",
        30: "warning",
        40: "error",
        999: "emergency",
    }
    assert TAG_LEVELS == {
        "debug": 10,
        "info": 20,
        "success": 25,
        "warning": 30,
        "error": 40,
        "emergency": 999,
    }


class TestPersistentMessage:
    def test_defaults(self) -> None:
        pm = PersistentMessage()
        assert pm.is_active
        assert pm.level == message_constants.INFO
        assert pm.is_dismissable
        assert pm.custom_tags == ""
        assert pm.default_tags == "persistent dismissable unsafe"
        assert pm.extra_tags == "persistent dismissable unsafe"
        assert pm.level_tag == "info"
        assert pm.tags == "persistent dismissable unsafe info"
        assert pm.message == pm.content
        assert pm.display_from is not None
        assert pm.display_until is None
        assert pm.target == pm.TargetType.AUTHENTICATED_ONLY

    @pytest.mark.parametrize(
        "dismissable,safe,expected",
        [
            (False, False, "persistent undismissable unsafe"),
            (False, True, "persistent undismissable safe"),
            (True, False, "persistent dismissable unsafe"),
            (True, True, "persistent dismissable safe"),
        ],
    )
    def test_default_tags(self, dismissable: bool, safe: bool, expected: str) -> None:
        pm = PersistentMessage(is_dismissable=dismissable, mark_content_safe=safe)
        assert pm.default_tags == expected

    @pytest.mark.parametrize(
        "custom_tags, expected",
        [
            ("", "persistent dismissable unsafe"),
            ("foo", "persistent dismissable unsafe foo"),
        ],
    )
    def test_extra_tags(self, custom_tags: str, expected: str) -> None:
        pm = PersistentMessage(custom_tags=custom_tags)
        assert pm.extra_tags == expected

    @pytest.mark.django_db
    def test_extra_tags__id_tag(self, pm: PersistentMessage) -> None:
        assert set(pm.extra_tags.split()) == {
            "persistent",
            "dismissable",
            "unsafe",
            pm.id_tag,
        }

    @pytest.mark.django_db
    def test_deactivate(self, pm: PersistentMessage) -> None:
        assert pm.is_active
        pm.deactivate()
        assert not pm.is_active
        assert pm.display_until is not None

    @pytest.mark.django_db
    def test_reactivate(self, pm: PersistentMessage) -> None:
        pm.deactivate()
        pm.reactivate()
        assert pm.is_active
        assert pm.display_until is None


@pytest.mark.django_db
class TestMessageDismissal:
    def test_dismiss(self, pm: PersistentMessage, user: User) -> None:
        assert not pm.dismissed_by.exists()
        assert not user.dismissed_messages.exists()
        pm.dismiss(user)
        assert pm.dismissed_by.filter(pk=user.pk).exists()
        assert user.dismissed_messages.get().message == pm
        # check that re-dismissing doesn't raise an exception
        pm.dismiss(user)
        assert user.dismissed_messages.count() == 1

    def test_dismiss__exception(self, pm: PersistentMessage, user: User) -> None:
        pm.is_dismissable = False
        with pytest.raises(UndismissableMessage):
            pm.dismiss(user)

    def test_dismiss__anon(self, pm: PersistentMessage) -> None:
        pm.dismiss(AnonymousUser)
        assert pm.dismissed_by.count() == 0


@pytest.mark.django_db
class TestPersistentMessageQuerySet:
    @pytest.mark.parametrize("start_offset,end_offset,count", [(0, 0, 1), (0, 1, 2)])
    def test_active(
        self, pm: PersistentMessage, start_offset: int, end_offset: int, count: int
    ) -> None:
        assert PersistentMessage.objects.active().get() == pm
        pm.deactivate()
        assert not PersistentMessage.objects.active().exists()
