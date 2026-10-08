from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditlog.services import AuditService
from core.pagination import (
    CustomPagination,
    paginate_list_data,
)
from organizations.mixins import (
    OrganizationQuerySetMixin,
)
from organizations.permissions import (
    ADMIN_ROLES,
    NETWORK_ROLES,
    READ_ONLY_ROLES,
    HasOrganizationRole,
)

from .models import MikrotikRouter
from .schemas import mikrotik_router_schema_view
from .serializers import MikrotikRouterSerializer
from .service.connection import MikrotikConnection
from .service.tools import (
    get_active_customers,
    get_customers,
    get_profiles,
)


def _router_audit_snapshot(router):
    """
    Return router information safe for audit storage.

    Passwords and other credentials are intentionally
    excluded.
    """

    return {
        "name": router.name,
        "host": router.host,
        "port": router.port,
        "username": router.username,
        "use_ssl": getattr(
            router,
            "use_ssl",
            False,
        ),
        "status": getattr(
            router,
            "status",
            "",
        ),
        "is_active": router.is_active,
        "description": getattr(
            router,
            "description",
            "",
        ),
    }


@mikrotik_router_schema_view
class MikrotikRouterViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = MikrotikRouter.objects.all()
    serializer_class = MikrotikRouterSerializer

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        "create": ADMIN_ROLES,
        "update": ADMIN_ROLES,
        "partial_update": ADMIN_ROLES,
        "destroy": ADMIN_ROLES,

        "test_connection": NETWORK_ROLES,
        "pppoe_customers": NETWORK_ROLES,
        "active_sessions": NETWORK_ROLES,
        "get_profiles": NETWORK_ROLES,
    }

    pagination_class = CustomPagination

    def perform_create(
        self,
        serializer,
    ):
        organization = self.get_organization()

        router = serializer.save(
            organization=organization
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="mikrotik.router_created",
            resource_type="MikrotikRouter",
            resource_id=router.pk,
            description=(
                f"MikroTik router "
                f"'{router.name}' created."
            ),
            metadata=_router_audit_snapshot(
                router
            ),
        )

    def perform_update(
        self,
        serializer,
    ):
        router = self.get_object()

        before = _router_audit_snapshot(
            router
        )

        router = serializer.save()

        after = _router_audit_snapshot(
            router
        )

        AuditService.log(
            organization=self.get_organization(),
            user=self.request.user,
            request=self.request,
            action="mikrotik.router_updated",
            resource_type="MikrotikRouter",
            resource_id=router.pk,
            description=(
                f"MikroTik router "
                f"'{router.name}' updated."
            ),
            metadata={
                "before": before,
                "after": after,
            },
        )

    def perform_destroy(
        self,
        instance,
    ):
        organization = self.get_organization()

        resource_id = instance.pk
        router_name = instance.name

        metadata = _router_audit_snapshot(
            instance
        )

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="mikrotik.router_deleted",
            resource_type="MikrotikRouter",
            resource_id=resource_id,
            description=(
                f"MikroTik router "
                f"'{router_name}' deleted."
            ),
            metadata=metadata,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def test_connection(
        self,
        request,
        pk=None,
    ):
        """
        Test connection to the MikroTik router.
        """

        router = self.get_object()

        try:
            conn = MikrotikConnection(
                host=router.host,
                port=router.port,
                username=router.username,
                password=router.password,
            )

            if conn.api:
                router.status = "connected"
                router.last_checked = timezone.now()

                router.save(
                    update_fields=[
                        "status",
                        "last_checked",
                        "updated_at",
                    ]
                )

                info = conn.get_router_info()

                AuditService.log(
                    organization=self.get_organization(),
                    user=request.user,
                    request=request,
                    action=(
                        "mikrotik.connection_test_succeeded"
                    ),
                    resource_type="MikrotikRouter",
                    resource_id=router.pk,
                    description=(
                        f"Connection test succeeded "
                        f"for router '{router.name}'."
                    ),
                    metadata={
                        "router": (
                            _router_audit_snapshot(
                                router
                            )
                        ),
                        "result": "success",
                    },
                )

                return Response(
                    {
                        "status": "success",
                        "message": (
                            "Successfully connected "
                            "to router"
                        ),
                        "router_info": info,
                    }
                )

            router.status = "error"
            router.last_checked = timezone.now()

            router.save(
                update_fields=[
                    "status",
                    "last_checked",
                    "updated_at",
                ]
            )

            AuditService.log(
                organization=self.get_organization(),
                user=request.user,
                request=request,
                action=(
                    "mikrotik.connection_test_failed"
                ),
                resource_type="MikrotikRouter",
                resource_id=router.pk,
                description=(
                    f"Connection test failed "
                    f"for router '{router.name}'."
                ),
                metadata={
                    "router": (
                        _router_audit_snapshot(
                            router
                        )
                    ),
                    "result": "failed",
                },
            )

            return Response(
                {
                    "status": "error",
                    "message": (
                        "Failed to connect to router"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:
            router.status = "error"
            router.last_checked = timezone.now()

            router.save(
                update_fields=[
                    "status",
                    "last_checked",
                    "updated_at",
                ]
            )

            AuditService.log(
                organization=self.get_organization(),
                user=request.user,
                request=request,
                action=(
                    "mikrotik.connection_test_failed"
                ),
                resource_type="MikrotikRouter",
                resource_id=router.pk,
                description=(
                    f"Connection test failed "
                    f"for router '{router.name}'."
                ),
                metadata={
                    "router": (
                        _router_audit_snapshot(
                            router
                        )
                    ),
                    "result": "failed",
                    "error_type": (
                        exc.__class__.__name__
                    ),
                },
            )

            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=["get"],
    )
    def pppoe_customers(
        self,
        request,
        pk=None,
    ):
        """
        Get all PPPoE secrets from the router.
        """

        router = self.get_object()

        try:
            conn = MikrotikConnection(
                host=router.host,
                port=router.port,
                username=router.username,
                password=router.password,
            )

            result = get_customers(
                conn.api
            )

            if result.get("status") == "Success":
                paginated = paginate_list_data(
                    result["customers"],
                    request,
                )

                customers_list = paginated.pop(
                    "results"
                )

                paginated_response = {
                    **paginated,
                    "status": result["status"],
                    "customers": customers_list,
                    "customers_count": result[
                        "customers_count"
                    ],
                }

                return Response(
                    paginated_response
                )

            return Response(
                result
            )

        except Exception as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=["get"],
    )
    def active_sessions(
        self,
        request,
        pk=None,
    ):
        """
        Get currently active PPPoE sessions.
        """

        router = self.get_object()

        try:
            conn = MikrotikConnection(
                host=router.host,
                port=router.port,
                username=router.username,
                password=router.password,
            )

            result = get_active_customers(
                conn.api
            )

            if result.get("status") == "Success":
                paginated = paginate_list_data(
                    result["customers"],
                    request,
                )

                customers_list = paginated.pop(
                    "results"
                )

                paginated_response = {
                    **paginated,
                    "status": result["status"],
                    "customers": customers_list,
                    "customers_count": result[
                        "customers_count"
                    ],
                }

                return Response(
                    paginated_response
                )

            return Response(
                result
            )

        except Exception as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=["get"],
    )
    def get_profiles(
        self,
        request,
        pk=None,
    ):
        """
        Get PPPoE profile names configured
        on this router.
        """

        router = self.get_object()

        try:
            conn = MikrotikConnection(
                host=router.host,
                port=router.port,
                username=router.username,
                password=router.password,
            )

            result = get_profiles(
                conn.api
            )

            if (
                result.get("status") == "Found"
                and result.get("profiles")
                is not None
            ):
                profile_names = [
                    profile["name"]
                    for profile in result["profiles"]
                    if "name" in profile
                ]

                return Response(
                    {
                        "status": "Success",
                        "profiles": profile_names,
                        "profiles_count": len(
                            profile_names
                        ),
                    }
                )

            return Response(
                result
            )

        except Exception as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )