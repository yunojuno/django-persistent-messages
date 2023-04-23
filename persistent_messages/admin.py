from django.contrib import admin

from .models import PersistentMessage


@admin.register(PersistentMessage)
class PersistentMessageAdmin(admin.ModelAdmin):
    list_display = ("content", "message_target", "display_from", "display_until")
    raw_id_fields = ("target_users", "target_groups", "dismissed_by")
    readonly_fields = ("created_at", "updated_at")
