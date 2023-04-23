from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, Group
from django.db import models
from django.template.defaultfilters import truncatechars_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext_lazy as _lazy

from .exceptions import UndismissableMessage

# mapped from django.contrib.messages
MESSAGE_LEVEL_CHOICES = [(v, k) for k, v in messages.DEFAULT_LEVELS.items()]


class PersistentQuerySet(models.QuerySet):
    def active(self) -> models.QuerySet[PersistentMessage]:
        """Filter messages to those that are currently active (based on dates)."""
        return self.filter(
            display_from__lte=tz_now(),
            display_until__gte=tz_now(),
        )

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
        if user.is_anonymous:
            return self.filter(message_target=PersistentMessage.TargetType.ALL_USERS)

        # If the user is authenticated then we build up the message filter using
        # the following logic: all messages that are targeted at all users, or
        # all authenticated users apply; messaages that are targeted at specific
        # users or groups apply if the user is in the target list;

        # filter on ALL_USERS messages as they are global
        all_filter = models.Q(message_target=PersistentMessage.TargetType.ALL_USERS)

        # filter on AUTHENTICATED_ONLY messages as we know the user is authenticated
        auth_filter = models.Q(
            message_target=PersistentMessage.TargetType.AUTHENTICATED_ONLY
        )

        # filter on messages targeted at the user
        user_filter = models.Q(
            message_target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_users=user,
        )

        # filter on messages targeted at the user via a group they belong to.
        # NB even though we are using another queryset in this filter, it's
        # evaluated on the fly as part of the overall query - we don't do
        # any extra queries here.
        group_filter = models.Q(
            message_target=PersistentMessage.TargetType.USERS_OR_GROUPS,
            target_groups__in=user.groups.all(),
        )

        # combine the filters together as an OR
        or_filter = all_filter | auth_filter | user_filter | group_filter

        # finally, exclude messages that have been dismissed by the user
        return self.exclude(dismissed_by=user).filter(or_filter)


class PersistentMessage(models.Model):
    """
    Wrap the Django message framework with some storage.

    Enables adding a message to the system which is repeatedly /
    persistently shown to all or certain users, unless they've had the
    opportunity to dismiss it.

    """

    class TargetType(models.TextChoices):
        ALL_USERS = "ALL_USERS", "All users, even logged out"
        AUTHENTICATED_ONLY = "AUTHENTICATED_USERS", "All logged-in users"
        USERS_OR_GROUPS = "USERS_OR_GROUPS", "Specific users or groups"

    content = models.TextField(blank=False)

    mark_content_safe = models.BooleanField(
        default=False,
        help_text=_lazy("Explicitly allow JS and/or HTML in this message."),
    )
    message_level = models.IntegerField(
        default=messages.INFO,
        choices=MESSAGE_LEVEL_CHOICES,
        help_text=_lazy(
            "The level of the message, mapped from django.contrib.messages.constants."
        ),
    )
    message_target = models.CharField(
        choices=TargetType.choices, default=TargetType.AUTHENTICATED_ONLY, max_length=50
    )
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        help_text=_lazy(
            "Specific users to target - used when message_target is USERS_OR_GROUPS"
        ),
        related_name="persistent_messages",
        blank=True,
    )
    target_groups = models.ManyToManyField(
        Group,
        help_text=_lazy(
            "Specific groups to target - used when message_target is USERS_OR_GROUPS"
        ),
        related_name="persistent_messages",
        blank=True,
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
    additional_extra_tags = models.CharField(
        max_length=100,
        blank=True,
        help_text=_lazy(
            "Space-separated tags to add to the default extra tags "
            "('persistent', 'dismissable')."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PersistentQuerySet.as_manager()

    def __str__(self) -> str:
        return f'"{truncatechars_html(self.content, 50)}"'

    @property
    def is_active(self) -> bool:
        if self.display_until:
            return self.display_from < tz_now() < self.display_until
        return self.display_from < tz_now()

    @property
    def default_extra_tags(self) -> str:
        if self.is_dismissable:
            return "persistent dismissable"
        return "persistent"

    @property
    def extra_tags(self) -> str:
        """
        Return the extra tags for this message.

        These tags are added to the message in the message store, so that
        they can be used in the output. Every messages gets a default tag
        "persistent", and "dismissable" if the message is dismissable.

        """
        return " ".join([self.default_extra_tags, self.additional_extra_tags])

    @property
    def message(self) -> str:
        """Return the message content, with HTML escaped if required."""
        if self.mark_content_safe:
            return mark_safe(self.content)  # noqa: S308
        return self.content

    def dismiss(self, user: settings.AUTH_USER_MODEL) -> None:
        """
        Dismiss this message for the given user.

        If the message is not dismissable, raises an exception.

        """
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


def get_user_messages(
    user: settings.AUTH_USER_MODEL | AnonymousUser,
) -> models.QuerySet[PersistentMessage]:
    """
    Return the messages for the given user.

    If the user is not authenticated, only messages targeted at all users
    will be returned.

    """
    return PersistentMessage.objects.filter_user(user).active()
