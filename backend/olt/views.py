from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditlog.services import AuditService
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


def _olt_audit_snapshot(olt):
    """
    Safe OLT metadata for audit storage.

    Credentials and SNMP community values are
    intentionally excluded.
    """

    return {
        "name": olt.name,
        "host": olt.host,
        "telnet_port": olt.telnet_port,
        "web_port": olt.web_port,
        "protocol": olt.protocol,
        "olt_type": olt.olt_type,
        "snmp_port": olt.snmp_port,
        "timeout": olt.timeout,
        "status": olt.status,
        "description": olt.description,
        "is_active": olt.is_active,
    }


def _onu_audit_snapshot(onu):
    """
    Safe ONU metadata for audit storage.
    """

    return {
        "olt_id": onu.olt_id,
        "onu_index": onu.onu_index,
        "serial_number": getattr(
            onu,
            "serial_number",
            "",
        ),
        "name": onu.name,
        "pon_port": onu.pon_port,
        "status": onu.status,
        "customer_id": onu.customer_id,
        "description": onu.description,
    }


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
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,
        "onus": READ_ONLY_ROLES,

        "create": NETWORK_ROLES,
        "update": NETWORK_ROLES,
        "partial_update": NETWORK_ROLES,

        "destroy": ADMIN_ROLES,

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

    def perform_create(
        self,
        serializer,
    ):
        organization = self.get_organization()

        olt = serializer.save(
            organization=organization
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="olt.device_created",
            resource_type="OltDevice",
            resource_id=olt.pk,
            description=(
                f"OLT '{olt.name}' created."
            ),
            metadata=_olt_audit_snapshot(
                olt
            ),
        )

    def perform_update(
        self,
        serializer,
    ):
        olt = self.get_object()

        before = _olt_audit_snapshot(
            olt
        )

        olt = serializer.save()

        after = _olt_audit_snapshot(
            olt
        )

        AuditService.log(
            organization=self.get_organization(),
            user=self.request.user,
            request=self.request,
            action="olt.device_updated",
            resource_type="OltDevice",
            resource_id=olt.pk,
            description=(
                f"OLT '{olt.name}' updated."
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
        olt_name = instance.name
        metadata = _olt_audit_snapshot(
            instance
        )

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="olt.device_deleted",
            resource_type="OltDevice",
            resource_id=resource_id,
            description=(
                f"OLT '{olt_name}' deleted."
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
            message = diagnostic_message(
                olt,
                snmp,
            )

            AuditService.log(
                organization=self.get_organization(),
                user=request.user,
                request=request,
                action="olt.connection_test_failed",
                resource_type="OltDevice",
                resource_id=olt.pk,
                description=(
                    f"OLT connection test failed "
                    f"for '{olt.name}'."
                ),
                metadata={
                    "olt": _olt_audit_snapshot(
                        olt
                    ),
                    "result": "failed",
                },
            )

            return Response(
                {
                    "status": "error",
                    "message": message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        AuditService.log(
            organization=self.get_organization(),
            user=request.user,
            request=request,
            action="olt.connection_test_succeeded",
            resource_type="OltDevice",
            resource_id=olt.pk,
            description=(
                f"OLT connection test succeeded "
                f"for '{olt.name}'."
            ),
            metadata={
                "olt": _olt_audit_snapshot(
                    olt
                ),
                "result": "success",
            },
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

            AuditService.log(
                organization=self.get_organization(),
                user=request.user,
                request=request,
                action="olt.onu_sync_succeeded",
                resource_type="OltDevice",
                resource_id=olt.pk,
                description=(
                    f"ONU sync completed for "
                    f"OLT '{olt.name}'."
                ),
                metadata={
                    "result": "success",
                    "created": result.get(
                        "created",
                        0,
                    ),
                    "updated": result.get(
                        "updated",
                        0,
                    ),
                },
            )

            return Response(
                result
            )

        AuditService.log(
            organization=self.get_organization(),
            user=request.user,
            request=request,
            action="olt.onu_sync_failed",
            resource_type="OltDevice",
            resource_id=olt.pk,
            description=(
                f"ONU sync failed for "
                f"OLT '{olt.name}'."
            ),
            metadata={
                "result": "failed",
            },
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
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        "create": NETWORK_ROLES,
        "update": NETWORK_ROLES,
        "partial_update": NETWORK_ROLES,

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

    def perform_create(
        self,
        serializer,
    ):
        organization = get_user_organization(
            self.request.user
        )

        onu = serializer.save()

        if onu.olt.organization_id != organization.id:
            onu.delete()

            raise ValueError(
                "ONU organization mismatch."
            )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="olt.onu_created",
            resource_type="Onu",
            resource_id=onu.pk,
            description=(
                f"ONU '{onu.name}' created."
            ),
            metadata=_onu_audit_snapshot(
                onu
            ),
        )

    def perform_update(
        self,
        serializer,
    ):
        organization = get_user_organization(
            self.request.user
        )

        onu = self.get_object()

        before = _onu_audit_snapshot(
            onu
        )

        onu = serializer.save()

        if onu.olt.organization_id != organization.id:
            raise ValueError(
                "ONU organization mismatch."
            )

        after = _onu_audit_snapshot(
            onu
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="olt.onu_updated",
            resource_type="Onu",
            resource_id=onu.pk,
            description=(
                f"ONU '{onu.name}' updated."
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
        organization = get_user_organization(
            self.request.user
        )

        resource_id = instance.pk
        onu_name = instance.name

        metadata = _onu_audit_snapshot(
            instance
        )

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="olt.onu_deleted",
            resource_type="Onu",
            resource_id=resource_id,
            description=(
                f"ONU '{onu_name}' deleted."
            ),
            metadata=metadata,
        )