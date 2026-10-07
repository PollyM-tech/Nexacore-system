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
        # Staff may inspect configured gateways.
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        # Gateway credentials/configuration are
        # administrative infrastructure settings.
        "create": ADMIN_ROLES,
        "update": ADMIN_ROLES,
        "partial_update": ADMIN_ROLES,
        "destroy": ADMIN_ROLES,

        # Changing the default gateway and sending
        # gateway tests are also admin-only.
        "set_default": ADMIN_ROLES,
        "test": ADMIN_ROLES,
    }

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

        gateway.is_default = True
        gateway.is_active = True

        gateway.save()

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

        return Response(
            SmsLogSerializer(
                log
            ).data,
            status=(
                status.HTTP_200_OK
                if log.status == "sent"
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
        # All staff can view templates.
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        # Billing staff often maintain payment,
        # reminder and account-notice templates.
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
        # Provider metadata is safe for staff
        # to inspect.
        "providers": READ_ONLY_ROLES,

        # Owner/admin/billing/support may send.
        # Technician and viewer may not.
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

        return Response(
            result
        )