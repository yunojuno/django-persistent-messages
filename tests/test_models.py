from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ValidationError
from django.test import override_settings

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

    def test_custom_group_query(self, user: User) -> None:
        """A message whose custom-group predicate passes is matched.

        tests/settings.py defines one group, "fred", keyed off first_name.
        """
        pm = PersistentMessage.objects.create(
            content="Hello Fred",
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_custom_group="fred",
        )
        user.first_name = "Fred"

        matched = PersistentMessage.objects.filter(
            PersistentMessage.objects.custom_group_query(user)
        )

        assert list(matched) == [pm]

    @pytest.mark.parametrize("custom_groups", [{}, None])
    def test_custom_group_query__no_groups_configured_runs_no_query(
        self,
        user: User,
        django_assert_num_queries: Any,
        custom_groups: dict | None,
    ) -> None:
        """No configured groups means no stored message can match.

        clean() only allows a target_custom_group that exists in
        MESSAGE_CUSTOM_GROUPS, so with the setting empty (or absent, which
        is how most projects run) the query this used to evaluate could not
        return a row. filter_user() calls this every time, and for a
        project rendering site-wide banners that is once per page.

        `None` covers a project that sets it to nothing; see the sibling
        test for one that has never defined it at all.
        """
        PersistentMessage.objects.create(
            content="Hello Fred",
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_custom_group="fred",
        )

        with override_settings(MESSAGE_CUSTOM_GROUPS=custom_groups):
            with django_assert_num_queries(0):
                query = PersistentMessage.objects.custom_group_query(user)
            assert not PersistentMessage.objects.filter(query).exists()

    def test_custom_group_query__setting_undefined(
        self, user: User, django_assert_num_queries: Any
    ) -> None:
        """The setting is optional, and absent is the common case.

        Deleting the attribute inside override_settings is how a project
        that has never declared MESSAGE_CUSTOM_GROUPS is reproduced -
        override_settings cannot express it, and this is the case the
        getattr default exists for.
        """
        PersistentMessage.objects.create(
            content="Hello Fred",
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_custom_group="fred",
        )

        with override_settings():
            del settings.MESSAGE_CUSTOM_GROUPS
            with django_assert_num_queries(0):
                query = PersistentMessage.objects.custom_group_query(user)
            assert not PersistentMessage.objects.filter(query).exists()

    @pytest.mark.parametrize(
        "user_is_anonymous,expected_queries", [(True, 1), (False, 1)]
    )
    def test_filter_user__no_groups_configured_costs_one_query(
        self,
        pm: PersistentMessage,
        user: User,
        django_assert_num_queries: Any,
        user_is_anonymous: bool,
        expected_queries: int,
    ) -> None:
        """The whole point of the short-circuit, from the caller's side.

        Before it, every filter_user() cost two queries however the
        setting was configured: the message lookup, plus the one
        custom_group_query evaluated eagerly to build its Q.
        """
        pm.target = PersistentMessage.TargetType.ALL_USERS
        pm.save()
        subject = AnonymousUser() if user_is_anonymous else user

        with override_settings(MESSAGE_CUSTOM_GROUPS={}):
            with django_assert_num_queries(expected_queries):
                assert list(PersistentMessage.objects.filter_user(subject)) == [pm]

    def test_clean__no_groups_configured(self) -> None:
        """An unknown group is a ValidationError, not an AttributeError.

        MESSAGE_CUSTOM_GROUPS is optional, so a project that has never
        defined it should still get a readable form error here.
        """
        pm = PersistentMessage(
            content="Hello Fred",
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_custom_group="fred",
        )

        with override_settings(MESSAGE_CUSTOM_GROUPS=None):
            with pytest.raises(ValidationError):
                pm.clean()
