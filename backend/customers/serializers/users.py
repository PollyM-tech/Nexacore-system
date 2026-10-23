from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import exceptions, serializers

from auth_kit.serializers.login_factors import LoginRequestSerializer
from auth_kit.serializers.user import UserSerializer
from organizations.models import OrganizationMembership


class EmailOnlyLoginRequestSerializer(LoginRequestSerializer):
    username = None
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(style={"input_type": "password"}, write_only=True, trim_whitespace=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        serializers.Serializer.__init__(self, *args, **kwargs)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs.get("email")
        password = attrs.get("password")

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise exceptions.ValidationError("Unable to log in with provided credentials.")

        if not user.check_password(password):
            raise exceptions.ValidationError("Unable to log in with provided credentials.")

        if not user.is_active:
            raise exceptions.ValidationError("User account is disabled.")

        self.validate_email_verification_status(user)
        self.context["user"] = user
        return attrs

class StaffIdentitySerializer(UserSerializer):
    """Expose verified display roles without allowing privilege updates."""

    is_platform_admin = serializers.BooleanField(source="is_superuser", read_only=True)
    membership = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = (*UserSerializer.Meta.fields, "is_platform_admin", "membership")

    def get_membership(self, user):
        # Match the active-organization selection used by tenant endpoints.
        membership = OrganizationMembership.objects.select_related("organization").filter(
            user=user, is_active=True, organization__is_active=True,
        ).first()
        if membership is None:
            return None
        return {
            "role": membership.role,
            "role_label": membership.get_role_display(),
            "organization": {
                "id": membership.organization_id,
                "name": membership.organization.name,
                "slug": membership.organization.slug,
            },
        }
