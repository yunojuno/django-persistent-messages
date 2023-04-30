from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from .models import MessageDismissal, PersistentMessage


@admin.register(PersistentMessage)
class PersistentMessageAdmin(admin.ModelAdmin):
    list_display = (
        "content",
        "target",
        "level_tag",
        "display_from",
        "display_until",
        "_is_active",
    )
    raw_id_fields = ("target_users", "target_groups", "dismissed_by")
    readonly_fields = (
        "_level_tag",
        "_extra_tags",
        "_tags",
        "_message",
        "_dissmissed_by_count",
        "created_at",
        "updated_at",
    )
    search_fields = ("content",)
    actions = ("deactivate_messages", "reactivate_messages")
    list_filter = ("level", "target", "is_dismissable", "mark_content_safe")

    @admin.display(boolean=True)
    def _is_active(self, obj: PersistentMessage) -> bool:
        return obj.is_active

    @admin.display(description="Message")
    def _message(self, obj: PersistentMessage) -> str:
        return mark_safe(f"<blockquote>{obj.message}</blockquote>")  # noqa: S308

    @admin.display(description="Level tag")
    def _level_tag(self, obj: PersistentMessage) -> str:
        return mark_safe(f"<code>{obj.level_tag}</code>")  # noqa: S308

    @admin.display(description="Extra tags")
    def _extra_tags(self, obj: PersistentMessage) -> str:
        return mark_safe(f"<code>{obj.extra_tags}</code>")  # noqa: S308

    @admin.display(description="All tags")
    def _tags(self, obj: PersistentMessage) -> str:
        return mark_safe(f"<code>{obj.tags}</code>")  # noqa: S308

    @admin.display(description="Dismissed by (# users)")
    def _dissmissed_by_count(self, obj: PersistentMessage) -> str:
        return obj.dismissed_by.count()

    @admin.action(description="Deactivate selected persistent messages")
    def deactivate_messages(
        self, request: HttpRequest, queryset: QuerySet[PersistentMessage]
    ) -> None:
        count = 0
        for obj in queryset:
            obj.deactivate()
            count += 1
        self.message_user(request, f"Successfully deactivated {count} message(s).")

    @admin.action(description="Reactivate selected persistent messages")
    def reactivate_messages(
        self, request: HttpRequest, queryset: QuerySet[PersistentMessage]
    ) -> None:
        count = 0
        for obj in queryset:
            obj.reactivate()
            count += 1
        self.message_user(request, f"Successfully deactivated {count} message(s).")


@admin.register(MessageDismissal)
class MessageDismissalAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "dismissed_at")
    search_fields = (
        "message__content",
        "user__first_name",
        "user__last_name",
    )
    list_filter = ("message__target", "dismissed_at")
