from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "organization",
        "user",
        "actor_role",
        "action",
        "resource_type",
        "resource_id",
    ]

    list_filter = [
        "action",
        "actor_role",
        "resource_type",
        "created_at",
    ]

    search_fields = [
        "user__username",
        "organization__name",
        "description",
        "resource_type",
        "resource_id",
    ]

    readonly_fields = [
        "organization",
        "user",
        "actor_role",
        "action",
        "resource_type",
        "resource_id",
        "description",
        "request_method",
        "request_path",
        "ip_address",
        "user_agent",
        "metadata",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False