from rest_framework.permissions import BasePermission

from .models import OrganizationMembership


OWNER = "owner"
ADMIN = "admin"
TECHNICIAN = "technician"
BILLING = "billing"
SUPPORT = "support"
VIEWER = "viewer"


ALL_STAFF_ROLES = {
    OWNER,
    ADMIN,
    TECHNICIAN,
    BILLING,
    SUPPORT,
    VIEWER,
}

ADMIN_ROLES = {
    OWNER,
    ADMIN,
}

NETWORK_ROLES = {
    OWNER,
    ADMIN,
    TECHNICIAN,
}

BILLING_ROLES = {
    OWNER,
    ADMIN,
    BILLING,
}

SUPPORT_ROLES = {
    OWNER,
    ADMIN,
    SUPPORT,
}

READ_ONLY_ROLES = ALL_STAFF_ROLES


class HasOrganizationRole(BasePermission):
    """
    Enforce organization membership roles.

    Views can define:

        role_permissions = {
            "list": READ_ONLY_ROLES,
            "retrieve": READ_ONLY_ROLES,
            "create": ADMIN_ROLES,
        }

    For APIViews, HTTP method names may be used:

        role_permissions = {
            "get": READ_ONLY_ROLES,
            "post": NETWORK_ROLES,
        }

    A "default" entry can be provided as a fallback.
    """

    message = (
        "You do not have permission to perform "
        "this action for this organization."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        membership = (
            OrganizationMembership.objects
            .select_related("organization")
            .filter(
                user=user,
                is_active=True,
                organization__is_active=True,
            )
            .first()
        )

        if membership is None:
            return False

        role_permissions = getattr(
            view,
            "role_permissions",
            None,
        )

        if not role_permissions:
            return False

        action = getattr(view, "action", None)

        permission_key = (
            action
            if action
            else request.method.lower()
        )

        allowed_roles = role_permissions.get(
            permission_key
        )

        if allowed_roles is None:
            allowed_roles = role_permissions.get(
                "default"
            )

        if allowed_roles is None:
            return False

        return membership.role in set(allowed_roles)