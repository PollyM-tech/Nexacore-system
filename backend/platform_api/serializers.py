from django.contrib.auth import get_user_model
from rest_framework import serializers
from auditlog.models import AuditLog
from organizations.models import Organization, OrganizationMembership
from .redaction import redact_metadata


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "username", "first_name", "last_name"]
        read_only_fields = fields


class PlatformUserSerializer(IdentitySerializer):
    membership_count = serializers.IntegerField(read_only=True)

    class Meta(IdentitySerializer.Meta):
        fields = IdentitySerializer.Meta.fields + [
            "is_active", "is_superuser", "date_joined", "last_login", "membership_count",
        ]
        read_only_fields = fields


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    customer_count = serializers.IntegerField(read_only=True)
    router_count = serializers.IntegerField(read_only=True)
    package_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "organization_type", "status", "is_active",
            "phone_number", "email", "country", "currency", "timezone",
            "created_at", "updated_at", "member_count", "customer_count", "router_count", "package_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        # Tenant access currently checks is_active, not status. Keep lifecycle
        # writes coherent without changing ordinary tenant endpoint semantics.
        if "status" in attrs:
            active = attrs["status"] == "active"
            if "is_active" in attrs and attrs["is_active"] != active:
                raise serializers.ValidationError({"is_active": "Must agree with organization status."})
            attrs["is_active"] = active
        elif "is_active" in attrs:
            attrs["status"] = "active" if attrs["is_active"] else "inactive"
        return attrs


class MembershipSerializer(serializers.ModelSerializer):
    user = IdentitySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), source="user", write_only=True, required=True,
    )

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "user_id", "role", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []  # Organization comes from the nested route under a lock.

    def validate(self, attrs):
        if self.instance is not None and "user" in attrs and attrs["user"].pk != self.instance.user_id:
            raise serializers.ValidationError({"user_id": "Membership identity cannot be changed. Add another membership instead."})
        return attrs


class PlatformAuditSerializer(serializers.ModelSerializer):
    actor = IdentitySerializer(source="user", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True, default=None)
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "actor", "actor_role", "organization", "organization_name",
            "action", "resource_type", "resource_id", "created_at", "metadata",
        ]
        read_only_fields = fields

    def get_metadata(self, obj):
        return redact_metadata(obj.metadata)
