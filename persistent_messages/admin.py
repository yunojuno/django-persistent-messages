from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import PersistentMessage


@admin.register(PersistentMessage)
class PersistentMessageAdmin(admin.ModelAdmin):
    list_display = (
        "content",
        "message_target",
        "display_from",
        "display_until",
        "_is_active",
    )
    raw_id_fields = ("target_users", "target_groups", "dismissed_by")
    readonly_fields = ("created_at", "updated_at")
    actions = ("deactivate_messages", "reactivate_messages")

    @admin.display(boolean=True)
    def _is_active(self, obj: PersistentMessage) -> bool:
        return obj.is_active

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
