from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AbstractBaseUser, Group
from django.db import models
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext_lazy as _lazy

# mapped from django.contrib.messages
MESSAGE_LEVEL_CHOICES = [(v, k) for k, v in messages.DEFAULT_LEVELS.items()]


class PersistentQuerySet(models.QuerySet):
    def filter_user(self, user: AbstractBaseUser) -> models.QuerySet[PersistentMessage]:
        """
        Filter messages to those which should be shown to the given user.

        This is a combination messages that are "all users" and messages that
        are targeted at the given user, or any group the user is a member of.

        """
        if user.is_anonymous:
            return self.filter(message_target=PersistentMessage.TargetType.ALL_USERS)
        # exclude messages that the user has already dismissed.
        qs = self.exclude(dismissed_by=user)
        # exclude any messages are targeted
        return self.get_queryset().filter_user()


class PersistentMessage(models.Model):
    """
    Wrap the Django message framework with some storage.

    Enables adding a message to the system which is repeatedly/persistently
    shown to all or certain users, unless they've had the opportunity to dismiss
    it.

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
        related_name="dismissed_persistent_messages",
        blank=True,
        help_text=_lazy("Users who have dismissed this message."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
