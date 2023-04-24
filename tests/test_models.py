import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import constants as message_constants

from persistent_messages.exceptions import UndismissableMessage
from persistent_messages.models import PersistentMessage


class TestPersistentMessage:
    def test_defaults(self) -> None:
        pm = PersistentMessage()
        assert pm.is_active
        assert pm.level == pm.message_level == message_constants.INFO
        assert pm.is_dismissable
        assert pm.default_extra_tags == "persistent dismissable"
        assert pm.additional_extra_tags == ""
        assert pm.extra_tags == "persistent dismissable"
        assert pm.additional_extra_tags == ""
        assert pm.message == pm.content
        assert pm.display_from is not None
        assert pm.display_until is None
        assert pm.message_target == pm.TargetType.AUTHENTICATED_ONLY

    @pytest.mark.parametrize(
        "is_dismissable, additional_extra_tags, extra_tags",
        [
            (True, "", "persistent dismissable"),
            (False, "", "persistent undismissable"),
            (False, "foo", "persistent undismissable foo"),
        ],
    )
    def test_extra_tags(
        self, is_dismissable: bool, additional_extra_tags: str, extra_tags: str
    ) -> None:
        pm = PersistentMessage(
            is_dismissable=is_dismissable,
            additional_extra_tags=additional_extra_tags,
        )
        assert pm.extra_tags == extra_tags

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
