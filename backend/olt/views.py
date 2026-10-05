from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from organizations.mixins import OrganizationQuerySetMixin
from organizations.permissions import (
    ADMIN_ROLES,
    NETWORK_ROLES,
    READ_ONLY_ROLES,
    HasOrganizationRole,
)
from organizations.services import get_user_organization

from .models import OltDevice, Onu
from .serializers import (
    OltDeviceSerializer,
    OnuSerializer,
)
from .service.snmp import (
    OltSnmp,
    diagnostic_message,
)
from .service.sync import sync_onus


class OltDeviceViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = OltDevice.objects.all()
    serializer_class = OltDeviceSerializer

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        # All organization staff may inspect OLTs.
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,
        "onus": READ_ONLY_ROLES,

        # Network infrastructure management.
        "create": NETWORK_ROLES,
        "update": NETWORK_ROLES,
        "partial_update": NETWORK_ROLES,

        # Destructive infrastructure operations
        # remain owner/admin only.
        "destroy": ADMIN_ROLES,

        # Operational network actions.
        "test_connection": NETWORK_ROLES,
        "sync_onus": NETWORK_ROLES,
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]

    filterset_fields = [
        "olt_type",
        "status",
        "is_active",
    ]

    search_fields = [
        "name",
        "host",
    ]

    @action(
        detail=True,
        methods=["post"],
    )
    def test_connection(
        self,
        request,
        pk=None,
    ):
        olt = self.get_object()

        snmp = OltSnmp(
            olt.host,
            olt.snmp_community,
            olt.snmp_port,
            timeout=olt.timeout or 10,
        )

        info = snmp.system_info()

        olt.status = (
            "online"
            if info
            else "error"
        )

        olt.last_checked = timezone.now()

        olt.save(
            update_fields=[
                "status",
                "last_checked",
                "updated_at",
            ]
        )

        if not info:
            return Response(
                {
                    "status": "error",
                    "message": diagnostic_message(
                        olt,
                        snmp,
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "online",
                "system_info": info,
            }
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def sync_onus(
        self,
        request,
        pk=None,
    ):
        olt = self.get_object()

        result = sync_onus(
            olt
        )

        if result.get("ok"):
            olt.status = "online"
            olt.last_checked = timezone.now()

            olt.save(
                update_fields=[
                    "status",
                    "last_checked",
                    "updated_at",
                ]
            )

            return Response(
                result
            )

        return Response(
            result,
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=True,
        methods=["get"],
    )
    def onus(
        self,
        request,
        pk=None,
    ):
        olt = self.get_object()

        queryset = (
            olt.onus
            .select_related(
                "customer"
            )
            .all()
        )

        serializer = OnuSerializer(
            queryset,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data
        )


class OnuViewSet(
    viewsets.ModelViewSet
):
    serializer_class = OnuSerializer

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        # Read access for all staff.
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        # ONU provisioning and editing are
        # network-operations responsibilities.
        "create": NETWORK_ROLES,
        "update": NETWORK_ROLES,
        "partial_update": NETWORK_ROLES,

        # Permanent deletion is restricted.
        "destroy": ADMIN_ROLES,
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]

    filterset_fields = [
        "olt",
        "status",
        "customer",
    ]

    search_fields = [
        "serial_number",
        "name",
        "onu_index",
        "pon_port",
    ]

    def get_queryset(self):
        organization = get_user_organization(
            self.request.user
        )

        return (
            Onu.objects
            .filter(
                olt__organization=organization
            )
            .select_related(
                "olt",
                "customer",
            )
        )