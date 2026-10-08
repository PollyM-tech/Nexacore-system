from django_filters.rest_framework import (
    DjangoFilterBackend,
)
from rest_framework import (
    filters,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response

from auditlog.services import AuditService
from organizations.mixins import (
    OrganizationQuerySetMixin,
)
from organizations.permissions import (
    ADMIN_ROLES,
    BILLING_ROLES,
    READ_ONLY_ROLES,
    SUPPORT_ROLES,
    HasOrganizationRole,
)
from organizations.services import (
    get_user_organization,
)

from .models import (
    SmsGateway,
    SmsLog,
    SmsTemplate,
)
from .providers import provider_metadata
from .recipients import resolve_recipients
from .serializers import (
    SendSmsSerializer,
    SmsGatewaySerializer,
    SmsLogSerializer,
    SmsTemplateSerializer,
)
from .service import SmsService


SMS_SEND_ROLES = (
    BILLING_ROLES
    | SUPPORT_ROLES
)


def _gateway_audit_snapshot(
    gateway,
):
    """
    Return safe gateway configuration for audit
    storage.

    Credentials and API secrets are intentionally
    excluded.
    """

    return {
        "label": gateway.label,
        "provider": gateway.provider,
        "sender_id": gateway.sender_id,
        "is_active": gateway.is_active,
        "is_default": gateway.is_default,
    }


def _template_audit_snapshot(
    template,
):
    """
    Store template metadata without duplicating
    SMS body content into the audit history.
    """

    return {
        "name": template.name,
        "category": template.category,
    }


class SmsGatewayViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = SmsGateway.objects.all()

    serializer_class = (
        SmsGatewaySerializer
    )

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

        "set_default": ADMIN_ROLES,
        "test": ADMIN_ROLES,
    }

    def perform_create(
        self,
        serializer,
    ):
        organization = self.get_organization()

        gateway = serializer.save(
            organization=organization
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="sms.gateway_created",
            resource_type="SmsGateway",
            resource_id=gateway.pk,
            description=(
                f"SMS gateway "
                f"'{gateway.label}' created."
            ),
            metadata=_gateway_audit_snapshot(
                gateway
            ),
        )

    def perform_update(
        self,
        serializer,
    ):
        gateway = self.get_object()

        before = _gateway_audit_snapshot(
            gateway
        )

        gateway = serializer.save()

        after = _gateway_audit_snapshot(
            gateway
        )

        AuditService.log(
            organization=self.get_organization(),
            user=self.request.user,
            request=self.request,
            action="sms.gateway_updated",
            resource_type="SmsGateway",
            resource_id=gateway.pk,
            description=(
                f"SMS gateway "
                f"'{gateway.label}' updated."
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
        gateway_label = instance.label

        metadata = _gateway_audit_snapshot(
            instance
        )

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="sms.gateway_deleted",
            resource_type="SmsGateway",
            resource_id=resource_id,
            description=(
                f"SMS gateway "
                f"'{gateway_label}' deleted."
            ),
            metadata=metadata,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def set_default(
        self,
        request,
        pk=None,
    ):
        gateway = self.get_object()

        before = _gateway_audit_snapshot(
            gateway
        )

        gateway.is_default = True
        gateway.is_active = True

        gateway.save()

        AuditService.log(
            organization=self.get_organization(),
            user=request.user,
            request=request,
            action="sms.gateway_set_default",
            resource_type="SmsGateway",
            resource_id=gateway.pk,
            description=(
                f"SMS gateway "
                f"'{gateway.label}' set as default."
            ),
            metadata={
                "before": before,
                "after": (
                    _gateway_audit_snapshot(
                        gateway
                    )
                ),
            },
        )

        return Response(
            self.get_serializer(
                gateway
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def test(
        self,
        request,
        pk=None,
    ):
        organization = (
            self.get_organization()
        )

        gateway = self.get_object()

        mobile = request.data.get(
            "mobile"
        )

        message = (
            request.data.get(
                "message"
            )
            or
            "Test SMS from Lintech."
        )

        if not mobile:
            return Response(
                {
                    "detail": (
                        "mobile is required"
                    )
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        log = SmsService.send_one(
            organization=organization,
            mobile=mobile,
            message=message,
            gateway=gateway,
            user=request.user,
        )

        test_succeeded = (
            log.status == "sent"
        )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action=(
                "sms.gateway_test_succeeded"
                if test_succeeded
                else
                "sms.gateway_test_failed"
            ),
            resource_type="SmsGateway",
            resource_id=gateway.pk,
            description=(
                f"SMS gateway test "
                f"{'succeeded' if test_succeeded else 'failed'} "
                f"for '{gateway.label}'."
            ),
            metadata={
                "gateway": (
                    _gateway_audit_snapshot(
                        gateway
                    )
                ),
                "result": (
                    "success"
                    if test_succeeded
                    else "failed"
                ),
                "sms_log_id": log.pk,
            },
        )

        return Response(
            SmsLogSerializer(
                log
            ).data,
            status=(
                status.HTTP_200_OK
                if test_succeeded
                else
                status.HTTP_502_BAD_GATEWAY
            ),
        )


class SmsTemplateViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = SmsTemplate.objects.all()

    serializer_class = (
        SmsTemplateSerializer
    )

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        "create": BILLING_ROLES,
        "update": BILLING_ROLES,
        "partial_update": BILLING_ROLES,
        "destroy": BILLING_ROLES,
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]

    filterset_fields = [
        "category",
    ]

    search_fields = [
        "name",
        "body",
    ]

    def perform_create(
        self,
        serializer,
    ):
        organization = self.get_organization()

        template = serializer.save(
            organization=organization
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="sms.template_created",
            resource_type="SmsTemplate",
            resource_id=template.pk,
            description=(
                f"SMS template "
                f"'{template.name}' created."
            ),
            metadata=_template_audit_snapshot(
                template
            ),
        )

    def perform_update(
        self,
        serializer,
    ):
        template = self.get_object()

        before = _template_audit_snapshot(
            template
        )

        template = serializer.save()

        after = _template_audit_snapshot(
            template
        )

        AuditService.log(
            organization=self.get_organization(),
            user=self.request.user,
            request=self.request,
            action="sms.template_updated",
            resource_type="SmsTemplate",
            resource_id=template.pk,
            description=(
                f"SMS template "
                f"'{template.name}' updated."
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
        template_name = instance.name

        metadata = _template_audit_snapshot(
            instance
        )

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="sms.template_deleted",
            resource_type="SmsTemplate",
            resource_id=resource_id,
            description=(
                f"SMS template "
                f"'{template_name}' deleted."
            ),
            metadata=metadata,
        )


class SmsLogViewSet(
    OrganizationQuerySetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = (
        SmsLog.objects
        .all()
        .select_related(
            "customer",
            "sent_by",
        )
    )

    serializer_class = (
        SmsLogSerializer
    )

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]

    filterset_fields = [
        "status",
        "provider",
        "customer__customer_id",
    ]

    search_fields = [
        "mobile",
        "message",
    ]


class SmsSendViewSet(
    viewsets.ViewSet
):
    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "providers": READ_ONLY_ROLES,
        "send": SMS_SEND_ROLES,
    }

    def get_organization(self):
        return get_user_organization(
            self.request.user
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def providers(
        self,
        request,
    ):
        return Response(
            provider_metadata()
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def send(
        self,
        request,
    ):
        organization = (
            self.get_organization()
        )

        serializer = SendSmsSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = (
            serializer.validated_data
        )

        gateway = None

        gateway_id = data.get(
            "gateway"
        )

        if gateway_id:
            gateway = (
                SmsGateway.objects
                .filter(
                    organization=organization,
                    pk=gateway_id,
                    is_active=True,
                )
                .first()
            )

            if not gateway:
                return Response(
                    {
                        "detail": (
                            "SMS gateway not found."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )

        recipients = resolve_recipients(
            organization,
            data["audience"],
            data,
        )

        if not recipients:
            return Response(
                {
                    "detail": (
                        "No valid recipients "
                        "for this audience."
                    )
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        result = SmsService.send_bulk(
            organization=organization,
            recipients=recipients,
            message_template=data[
                "message"
            ],
            gateway=gateway,
            user=request.user,
        )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="sms.bulk_send",
            resource_type="SmsLog",
            resource_id="bulk",
            description=(
                f"Bulk SMS send requested for "
                f"{len(recipients)} recipient(s)."
            ),
            metadata={
                "audience": data["audience"],
                "recipient_count": len(
                    recipients
                ),
                "gateway_id": (
                    gateway.pk
                    if gateway
                    else None
                ),
                "gateway_provider": (
                    gateway.provider
                    if gateway
                    else None
                ),
                "result_status": (
                    result.get("status")
                    if isinstance(
                        result,
                        dict,
                    )
                    else None
                ),
                "sent": (
                    result.get("sent")
                    if isinstance(
                        result,
                        dict,
                    )
                    else None
                ),
                "failed": (
                    result.get("failed")
                    if isinstance(
                        result,
                        dict,
                    )
                    else None
                ),
            },
        )

        return Response(
            result
        )