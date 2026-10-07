from django_filters.rest_framework import (
    DjangoFilterBackend,
)
from rest_framework import (
    filters,
    viewsets,
)
from rest_framework.permissions import (
    IsAuthenticated,
)

from organizations.permissions import (
    ADMIN_ROLES,
    HasOrganizationRole,
)
from organizations.services import (
    get_user_organization,
)

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Organization-scoped immutable audit history.

    Owner and admin roles may view audit history.
    Audit records cannot be created, edited, or
    deleted through the API.
    """

    serializer_class = AuditLogSerializer

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": ADMIN_ROLES,
        "retrieve": ADMIN_ROLES,
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "action",
        "actor_role",
        "resource_type",
        "user",
    ]

    search_fields = [
        "description",
        "resource_type",
        "resource_id",
        "user__username",
    ]

    ordering_fields = [
        "created_at",
        "action",
        "resource_type",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        organization = get_user_organization(
            self.request.user
        )

        return (
            AuditLog.objects
            .filter(
                organization=organization
            )
            .select_related(
                "organization",
                "user",
            )
        )