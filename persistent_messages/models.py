from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.messages.utils import get_level_tags
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from .exceptions import UndismissableMessage

# use the contrib func as it pulls in settings overrides
LEVEL_TAGS = get_level_tags()
# invert the dict to get a tag -> level mapping
# NB this will fail if there are duplicate values in the original dict
TAG_LEVELS = {tag: level for level, tag in LEVEL_TAGS.items()}


def get_level(tag: str) -> int:
    """Convert a tag to a level."""
    return TAG_LEVELS[tag]


def get_tag(level: int) -> str:
    """Convert a level to a tag."""
    return LEVEL_TAGS[level]


class PersistentMessageQuerySet(models.QuerySet):
    def active(self) -> models.QuerySet[PersistentMessage]:
        """Filter messages to those that are currently active (based on dates)."""
        start_date_filter = models.Q(display_from__lte=tz_now())
        end_date_filter = models.Q(display_until__gte=tz_now()) | models.Q(
            display_until__isnull=True
        )
        return self.filter(start_date_filter).filter(end_date_filter)

    def custom_group_query(self, user: settings.AUTH_USER_MODEL) -> models.Q:
        """Return a Q object that can be used to filter messages for the given user."""
        messages = (
            self.filter(
                target=PersistentMessage.TargetType.USERS_OR_GROUPS,
                target_custom_group__isnull=False,
            )
            .exclude(target_custom_group="")
            .active()
        )
        return models.Q(id__in=[m.id for m in messages if m.user_in_custom_group(user)])

    def filter_user(
        self, user: settings.AUTH_USER_MODEL | AnonymousUser
    ) -> models.QuerySet[PersistentMessage]:
        """
        Filter messages to those which should be shown to the given user.

        This is a combination messages that are "all users" and messages
        that are targeted at the given user, or any group the user is a
        member of.

        NB There is a built-in assumption in this method that there will
        never be a large number of undismissed messages for a given
        user, and so iterating through them is not a problem.

        """
        messages = self.active()

        # filter on ALL_USERS messages as they are global
        all_filter = models.Q(target=PersistentMessage.TargetType.ALL_USERS)

        # custom user-attr filters - these need to be evaluated on the fly
        custom_filter = self.custom_group_query(user)

        if user.is_anonymous:
            # filter on ALL_USERS messages as they are global
            anon_filter = models.Q(target=PersistentMessage.TargetType.ANONYMOUS_ONLY)
            return messages.filter(all_filter | anon_filter | custom_filter)

        # If the user is authenticated then we build up the message filter using
        # the following logic: all messages that are targeted at all users, or
        # all authenticated users apply; messaages that are targeted at specific
        # users or groups apply if the user is in the target list;
        messages = messages.exclude(dismissed_by=user)

        # filter on AUTHENTICATED_ONLY messages as we know the user is authenticated
        auth_filter = models.Q(target=PersistentMessage.TargetType.AUTHENTICATED_ONLY)

        # filter on messages targeted at the user
        user_filter = models.Q(
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_users=user,
        )

        # filter on messages targeted at the user via a group they belong to.
        # NB even though we are using another queryset in this filter, it's
        # evaluated on the fly as part of the overall query - we don't do
        # any extra queries here.
        group_filter = models.Q(
            target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_groups__in=user.groups.all(),
        )

        # combine the filters together as an OR
        or_filter = (
            all_filter | auth_filter | user_filter | group_filter | custom_filter
        )

        return messages.filter(or_filter)


class PersistentMessageManager(models.Manager):
    def create(self, **kwargs: Any) -> Any:
        user = kwargs.pop("user", None)
        if user:
            kwargs["target"] = PersistentMessage.TargetType.USERS_OR_GROUPS
        obj = super().create(**kwargs)
        if user:
            obj.target_users.add(user)
        return obj


class PersistentMessage(models.Model):
    """
    Wrap the Django message framework with some storage.

    Enables adding a message to the system which is repeatedly /
    persistently shown to all or certain users, unless they've had the
    opportunity to dismiss it.

    """

    # convert to a list of tuples for use in a model field
    LEVEL_TAG_CHOICES = [(k, v) for k, v in LEVEL_TAGS.items()]

    class TargetType(models.TextChoices):
        ALL_USERS = "ALL_USERS", "All users, even logged out"
        AUTHENTICATED_ONLY = "AUTHENTICATED_USERS", "All logged-in users"
        ANONYMOUS_ONLY = "ANONYMOUS_USERS", "All anonymous users"
        USERS_OR_GROUPS = "USERS_OR_GROUPS", "Specific users or groups (inc. custom)"

    content = models.TextField(blank=False)

    mark_content_safe = models.BooleanField(
        default=False,
        help_text=_lazy("Explicitly allow JS and/or HTML in this message."),
    )
    level = models.IntegerField(
        default=messages.INFO,
        choices=LEVEL_TAG_CHOICES,
        help_text=_lazy(
            "The level of the message, mapped from django.contrib.messages.constants."
        ),
    )
    target = models.CharField(
        choices=TargetType.choices, default=TargetType.AUTHENTICATED_ONLY, max_length=50
    )
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        help_text=_lazy(
            "Specific users to target - used when target is USERS_OR_GROUPS"
        ),
        related_name="persistent_messages",
        blank=True,
    )
    target_groups = models.ManyToManyField(
        Group,
        help_text=_lazy(
            "Specific groups to target - used when target is USERS_OR_GROUPS"
        ),
        related_name="persistent_messages",
        blank=True,
    )
    target_custom_group = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom group to enable this flag for",
    )
    display_from = models.DateTimeField(
        help_text=_lazy("The earliest time this message should be shown."),
        default=tz_now,
    )
    display_until = models.DateTimeField(
        help_text=_lazy("The latest time this message should be shown."),
        blank=True,
        null=True,
    )
    is_dismissable = models.BooleanField(
        default=True,
        help_text=_lazy("Whether this message can be dismissed by the user."),
    )
    dismissed_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="MessageDismissal",
        help_text=_lazy("Users who have dismissed this message."),
    )
    custom_tags = models.CharField(
        max_length=100,
        blank=True,
        help_text=_lazy(
            "User-defined tags that are combined with the default_tags and "
            "passed to messages framework as extra_tags."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PersistentMessageManager.from_queryset(PersistentMessageQuerySet)()

    def __str__(self) -> str:
        return self.message

    def clean(self) -> None:
        if custom_group := self.target_custom_group:
            if custom_group not in settings.MESSAGE_CUSTOM_GROUPS:
                raise ValidationError(
                    _("Custom group not in settings.MESSAGE_CUSTOM_GROUPS")
                )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        if self.display_until:
            return self.display_from <= tz_now() < self.display_until
        return self.display_from <= tz_now()

    # === properties added for compatibility with the messages framework ===
    @property
    def tags(self) -> str:
        return " ".join(tag for tag in [self.extra_tags, self.level_tag] if tag)

    @property
    def level_tag(self) -> str:
        return LEVEL_TAGS.get(self.level, "")

    @property
    def message(self) -> str:
        """Return the message content, with HTML escaped if required."""
        if self.mark_content_safe:
            return mark_safe(self.content)  # noqa: S308
        return self.content

    # /=== properties added for compatibility with the messages framework ===

    @property
    def id_tag(self) -> str:
        """Return a unique pmid-* tag that is added to extra_tags."""
        return f"pmid-{self.id}" if self.id else ""

    @property
    def default_tags(self) -> str:
        """Return the tag derived from the message ('safe', 'persistent', etc.)."""
        tags = ["persistent"]
        if self.id_tag:
            tags.append(self.id_tag)
        tags.append("dismissable" if self.is_dismissable else "undismissable")
        tags.append("safe" if self.mark_content_safe else "unsafe")
        return " ".join(tags)

    @property
    def extra_tags(self) -> str:
        """Return custom_tags, default_tags combined."""
        all_tags = dict.fromkeys(
            self.default_tags.split() + self.custom_tags.strip().split()
        )
        return " ".join(all_tags.keys())

    def dismiss_url(self) -> str:
        """Return the URL to dismiss this message."""
        # you can't dismiss a message that hasn't been saved yet
        if not self.id:
            return ""
        if not self.is_dismissable:
            return ""
        return reverse("persistent_messages:dismiss_message", args=[self.id])

    def dismiss(self, user: settings.AUTH_USER_MODEL) -> None:
        """
        Dismiss this message for the given user.

        If the message is not dismissable, raises an exception.

        """
        if user.is_anonymous:
            return
        if not self.is_dismissable:
            raise UndismissableMessage
        self.dismissed_by.add(user)

    def deactivate(self) -> None:
        """Deactivate by setting the display_until property to now."""
        self.display_until = tz_now()
        self.save()

    def reactivate(self) -> None:
        """Deactivate by setting the display_until property to null."""
        self.display_until = None
        self.save()

    def user_in_custom_group(self, user: settings.AUTH_USER_MODEL) -> bool:
        if not self.target_custom_group:
            return False
        return settings.MESSAGE_CUSTOM_GROUPS[self.target_custom_group](user)


class MessageDismissal(models.Model):
    """Through table for user dismissals of messages."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dismissed_messages",
    )
    message = models.ForeignKey(
        PersistentMessage,
        on_delete=models.CASCADE,
        related_name="message_dismissals",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "message")
