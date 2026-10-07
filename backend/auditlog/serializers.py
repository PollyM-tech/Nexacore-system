from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(
    serializers.ModelSerializer
):
    username = serializers.SerializerMethodField()
    organization_name = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = AuditLog

        fields = [
            "id",
            "organization",
            "organization_name",
            "user",
            "username",
            "actor_role",
            "action",
            "resource_type",
            "resource_id",
            "description",
            "request_method",
            "request_path",
            "ip_address",
            "metadata",
            "created_at",
        ]

        read_only_fields = fields

    def get_username(
        self,
        obj,
    ):
        if not obj.user:
            return None

        return obj.user.get_username()

    def get_organization_name(
        self,
        obj,
    ):
        if not obj.organization:
            return None

        return obj.organization.name