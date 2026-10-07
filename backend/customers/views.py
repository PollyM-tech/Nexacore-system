from datetime import date, timedelta

from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditlog.services import AuditService
from core.pagination import CustomPagination
from organizations.mixins import OrganizationQuerySetMixin
from organizations.permissions import (
    ADMIN_ROLES,
    BILLING_ROLES,
    NETWORK_ROLES,
    READ_ONLY_ROLES,
    SUPPORT_ROLES,
    HasOrganizationRole,
)
from organizations.services import get_user_organization

from .models import (
    AddressZone,
    CustomerProfile,
    SupportTicket,
    TicketReply,
)
from .schemas import (
    admin_ticket_schema_view,
    customer_schema_view,
    zone_schema_view,
)
from .serializers import (
    AddressZoneCreateSerializer,
    AddressZoneSerializer,
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerLinkExistingSerializer,
    CustomerListSerializer,
)
from .serializers.tickets import (
    AdminSupportTicketDetailSerializer,
    AdminSupportTicketSerializer,
    TicketReplySerializer,
)
from .service import CustomerService


@customer_schema_view
class CustomerViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = CustomerProfile.objects.all()

    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        "create": BILLING_ROLES | NETWORK_ROLES,

        "update": ADMIN_ROLES,
        "partial_update": ADMIN_ROLES,
        "destroy": ADMIN_ROLES,

        "online_status": READ_ONLY_ROLES,

        "link_existing": NETWORK_ROLES,
        "live_stats": NETWORK_ROLES,
        "update_connection": NETWORK_ROLES,

        "update_billing": BILLING_ROLES,

        "update_status": BILLING_ROLES | NETWORK_ROLES,
    }

    lookup_field = "customer_id"

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer

        if self.action in [
            "retrieve",
            "update",
            "partial_update",
        ]:
            return CustomerDetailSerializer

        return CustomerCreateSerializer

    def get_queryset(self):
        organization = self.get_organization()

        queryset = CustomerService.get_all_customers(
            organization
        )

        params = self.request.query_params

        status_filter = params.get("status")

        if status_filter:
            queryset = queryset.filter(
                customer_status=status_filter
            )

        zone = params.get("zone")

        if zone:
            queryset = queryset.filter(
                zone_id=zone
            )

        if params.get("due"):
            queryset = queryset.filter(
                balance__lt=0
            )

        if params.get("free"):
            queryset = queryset.filter(
                customer_status="free"
            )

        if params.get("expired"):
            today = date.today()

            expired_ids = [
                customer.id
                for customer in queryset
                if customer.billing_date
                and (
                    customer.billing_date
                    + timedelta(
                        days=(
                            customer.extended_billing_days
                            or 0
                        )
                    )
                )
                < today
            ]

            queryset = queryset.filter(
                id__in=expired_ids
            )

        return queryset

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        organization = self.get_organization()

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer = CustomerService.create_customer(
            organization,
            serializer.validated_data,
        )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="customer.created",
            resource_type="CustomerProfile",
            resource_id=customer.customer_id,
            description=(
                f"Customer "
                f"'{customer.customer_name}' created."
            ),
            metadata={
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "phone_number": customer.phone_number,
                "status": customer.customer_status,
                "package_id": (
                    customer.package_id
                    if customer.package_id
                    else None
                ),
                "zone_id": (
                    customer.zone_id
                    if customer.zone_id
                    else None
                ),
            },
        )

        response_serializer = CustomerCreateSerializer(
            customer
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(
        self,
        request,
        *args,
        **kwargs,
    ):
        organization = self.get_organization()

        customer_id = kwargs.get(
            "customer_id"
        )

        instance = CustomerService.get_customer_details(
            organization,
            customer_id,
        )

        if not instance:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(
            instance
        )

        return Response(
            serializer.data
        )

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):
        organization = self.get_organization()

        customer_id = kwargs.get(
            "customer_id"
        )

        instance = CustomerService.get_customer_details(
            organization,
            customer_id,
        )

        if not instance:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        before = {
            "customer_name": instance.customer_name,
            "phone_number": instance.phone_number,
            "address": instance.address,
            "zone_id": instance.zone_id,
            "package_id": instance.package_id,
            "customer_status": instance.customer_status,
        }

        serializer = CustomerDetailSerializer(
            instance,
            data=request.data,
            partial=kwargs.get(
                "partial",
                False,
            ),
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer = serializer.save()

        after = {
            "customer_name": customer.customer_name,
            "phone_number": customer.phone_number,
            "address": customer.address,
            "zone_id": customer.zone_id,
            "package_id": customer.package_id,
            "customer_status": customer.customer_status,
        }

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="customer.updated",
            resource_type="CustomerProfile",
            resource_id=customer.customer_id,
            description=(
                f"Customer "
                f"'{customer.customer_name}' updated."
            ),
            metadata={
                "before": before,
                "after": after,
            },
        )

        return Response(
            serializer.data
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):
        organization = self.get_organization()

        customer_id = self.kwargs.get(
            "customer_id"
        )

        existing = (
            CustomerService.get_customer_details(
                organization,
                customer_id,
            )
        )

        if not existing:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        audit_metadata = {
            "customer_id": existing.customer_id,
            "customer_name": existing.customer_name,
            "phone_number": existing.phone_number,
            "status": existing.customer_status,
        }

        try:
            CustomerService.delete_customer_profile(
                organization,
                customer_id,
            )

            AuditService.log(
                organization=organization,
                user=request.user,
                request=request,
                action="customer.deleted",
                resource_type="CustomerProfile",
                resource_id=customer_id,
                description=(
                    f"Customer "
                    f"'{audit_metadata['customer_name']}' "
                    "deleted."
                ),
                metadata=audit_metadata,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT
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
        detail=False,
        methods=["get"],
        url_path="online_status",
    )
    def online_status(self, request):
        organization = self.get_organization()

        cache_key = (
            f"pppoe_online_names:"
            f"{organization.pk}"
        )

        cached = cache.get(
            cache_key
        )

        if cached is None:
            cached = list(
                CustomerService.get_online_pppoe_names(
                    organization
                )
            )

            cache.set(
                cache_key,
                cached,
                20,
            )

        return Response(
            {
                "online": cached,
            }
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def link_existing(self, request):
        organization = self.get_organization()

        serializer = CustomerLinkExistingSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer = (
            CustomerService.link_existing_customer(
                organization,
                serializer.validated_data,
            )
        )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="customer.pppoe_linked",
            resource_type="CustomerProfile",
            resource_id=customer.customer_id,
            description=(
                f"Customer "
                f"'{customer.customer_name}' linked "
                "to an existing PPPoE account."
            ),
            metadata={
                "customer_id": customer.customer_id,
            },
        )

        response_serializer = CustomerCreateSerializer(
            customer
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="update_billing",
    )
    def update_billing(
        self,
        request,
        customer_id=None,
    ):
        organization = self.get_organization()

        existing = (
            CustomerService.get_customer_details(
                organization,
                customer_id,
            )
        )

        if not existing:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        old_billing_date = (
            existing.billing_date.isoformat()
            if existing.billing_date
            else None
        )

        old_extended_days = (
            existing.extended_billing_days
        )

        billing_day = request.data.get(
            "billing_day"
        )

        extended = request.data.get(
            "extended_billing_days"
        )

        if billing_day is not None:
            try:
                billing_day_value = int(
                    billing_day
                )
            except (TypeError, ValueError):
                return Response(
                    {
                        "status": "error",
                        "message": (
                            "billing_day must be "
                            "an integer."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            if (
                billing_day_value < 1
                or billing_day_value > 28
            ):
                return Response(
                    {
                        "status": "error",
                        "message": (
                            "billing_day must be "
                            "between 1 and 28."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

        if extended is not None:
            try:
                extended_value = int(
                    extended
                )
            except (TypeError, ValueError):
                return Response(
                    {
                        "status": "error",
                        "message": (
                            "extended_billing_days "
                            "must be an integer."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            if extended_value < 0:
                return Response(
                    {
                        "status": "error",
                        "message": (
                            "extended_billing_days "
                            "cannot be negative."
                        ),
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

        customer = (
            CustomerService.update_billing_settings(
                organization,
                customer_id,
                billing_day,
                extended,
            )
        )

        if not customer:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="customer.billing_updated",
            resource_type="CustomerProfile",
            resource_id=customer.customer_id,
            description=(
                f"Billing settings updated for "
                f"'{customer.customer_name}'."
            ),
            metadata={
                "before": {
                    "billing_date": old_billing_date,
                    "extended_billing_days": (
                        old_extended_days
                    ),
                },
                "requested": {
                    "billing_day": billing_day,
                    "extended_billing_days": extended,
                },
                "after": {
                    "billing_date": (
                        customer.billing_date.isoformat()
                        if customer.billing_date
                        else None
                    ),
                    "extended_billing_days": (
                        customer.extended_billing_days
                    ),
                },
            },
        )

        return Response(
            CustomerDetailSerializer(
                customer
            ).data
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="live_stats",
    )
    def live_stats(
        self,
        request,
        customer_id=None,
    ):
        organization = self.get_organization()

        customer = (
            CustomerService.get_customer_details(
                organization,
                customer_id,
            )
        )

        if not customer:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        info = getattr(
            customer,
            "router_info",
            None,
        )

        if not info or not info.router:
            return Response(
                {
                    "status": "offline",
                    "live_stats_available": False,
                    "message": (
                        "No router/PPPoE configured "
                        "for this customer."
                    ),
                }
            )

        if (
            info.router.organization_id
            != organization.id
        ):
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Router organization mismatch."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from mikrotik.service.connection import (
            MikrotikConnection,
        )

        try:
            conn = MikrotikConnection(
                host=info.router.host,
                port=info.router.port,
                username=info.router.username,
                password=info.router.password,
            )

            if not conn.api:
                return Response(
                    {
                        "status": "offline",
                        "live_stats_available": False,
                        "message": (
                            "Unable to connect "
                            "to router."
                        ),
                    }
                )

            name = info.pppoe_name.lower()

            secret_list = (
                conn.api
                .get_resource(
                    "/ppp/secret"
                )
                .get(
                    name=name
                )
            )

            secret = (
                secret_list[0]
                if secret_list
                else {}
            )

            base = {
                "profile": secret.get(
                    "profile",
                    "unknown",
                ),
                "service": secret.get(
                    "service",
                    "pppoe",
                ),
                "last_logged_in": secret.get(
                    "last-logged-in",
                    "unknown",
                ),
                "last_logged_out": secret.get(
                    "last-logged-out",
                    "unknown",
                ),
                "last_caller": secret.get(
                    "last-caller-id",
                    secret.get(
                        "last-caller",
                        "unknown",
                    ),
                ),
                "last_disconnect_reason": (
                    secret.get(
                        "last-disconnect-reason",
                        "unknown",
                    )
                ),
                "limit_bytes_in": secret.get(
                    "limit-bytes-in",
                    "0",
                ),
                "limit_bytes_out": secret.get(
                    "limit-bytes-out",
                    "0",
                ),
                "disabled": secret.get(
                    "disabled",
                    "false",
                ),
            }

            active = (
                conn.api
                .get_resource(
                    "/ppp/active"
                )
                .get(
                    name=name
                )
            )

            if active:
                session = active[0]

                return Response(
                    {
                        **base,
                        "status": "online",
                        "live_stats_available": True,
                        "uptime": session.get(
                            "uptime",
                            "unknown",
                        ),
                        "bytes_in": session.get(
                            "bytes-in",
                            "0",
                        ),
                        "bytes_out": session.get(
                            "bytes-out",
                            "0",
                        ),
                        "packets_in": session.get(
                            "packets-in",
                            "0",
                        ),
                        "packets_out": session.get(
                            "packets-out",
                            "0",
                        ),
                        "caller_id": session.get(
                            "caller-id",
                            "unknown",
                        ),
                        "address": session.get(
                            "address",
                            "unknown",
                        ),
                        "session_id": session.get(
                            "session-id",
                            "unknown",
                        ),
                        "encoding": session.get(
                            "encoding",
                            "unknown",
                        ),
                    }
                )

            return Response(
                {
                    **base,
                    "status": "offline",
                    "live_stats_available": False,
                }
            )

        except Exception as exc:
            return Response(
                {
                    "status": "offline",
                    "live_stats_available": False,
                    "message": str(exc),
                }
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="update_status",
    )
    def update_status(
        self,
        request,
        customer_id=None,
    ):
        organization = self.get_organization()

        status_value = request.data.get(
            "status"
        )

        if status_value not in [
            "active",
            "disconnected",
        ]:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Invalid status value. "
                        "Allowed: active, disconnected"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = (
            CustomerService.get_customer_details(
                organization,
                customer_id,
            )
        )

        if not existing:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        old_status = existing.customer_status

        try:
            customer, warning = (
                CustomerService.update_customer_status(
                    organization,
                    customer_id,
                    status_value,
                )
            )

            AuditService.log(
                organization=organization,
                user=request.user,
                request=request,
                action="customer.status_changed",
                resource_type="CustomerProfile",
                resource_id=customer.customer_id,
                description=(
                    f"Customer "
                    f"'{customer.customer_name}' status "
                    f"changed from '{old_status}' "
                    f"to '{status_value}'."
                ),
                metadata={
                    "before": old_status,
                    "after": status_value,
                    "warning": warning or "",
                },
            )

            data = CustomerCreateSerializer(
                customer
            ).data

            if warning:
                data["warning"] = warning

            return Response(
                data,
                status=status.HTTP_200_OK,
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
        methods=["post"],
        url_path="update_connection",
    )
    def update_connection(
        self,
        request,
        customer_id=None,
    ):
        organization = self.get_organization()

        existing = (
            CustomerService.get_customer_details(
                organization,
                customer_id,
            )
        )

        if not existing:
            return Response(
                {
                    "status": "error",
                    "message": "Customer not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        old_info = getattr(
            existing,
            "router_info",
            None,
        )

        before = {
            "router_id": (
                old_info.router_id
                if old_info
                else None
            ),
            "pppoe_name": (
                old_info.pppoe_name
                if old_info
                else ""
            ),
        }

        try:
            customer, warning = (
                CustomerService.update_customer_connection(
                    organization,
                    customer_id,
                    request.data,
                )
            )

            instance = (
                CustomerService.get_customer_details(
                    organization,
                    customer.customer_id,
                )
            )

            new_info = getattr(
                instance,
                "router_info",
                None,
            )

            after = {
                "router_id": (
                    new_info.router_id
                    if new_info
                    else None
                ),
                "pppoe_name": (
                    new_info.pppoe_name
                    if new_info
                    else ""
                ),
            }

            AuditService.log(
                organization=organization,
                user=request.user,
                request=request,
                action="customer.connection_updated",
                resource_type="CustomerProfile",
                resource_id=customer.customer_id,
                description=(
                    f"Connection settings updated for "
                    f"'{customer.customer_name}'."
                ),
                metadata={
                    "before": before,
                    "after": after,
                    "warning": warning or "",
                },
            )

            data = CustomerDetailSerializer(
                instance
            ).data

            if warning:
                data["warning"] = warning

            return Response(
                data,
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            return Response(
                {
                    "status": "error",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@zone_schema_view
class AddressZoneViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = AddressZone.objects.all()

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

    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in [
            "list",
            "retrieve",
        ]:
            return AddressZoneSerializer

        return AddressZoneCreateSerializer

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        zone = serializer.save(
            organization=self.get_organization()
        )

        response_serializer = AddressZoneSerializer(
            zone
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.get(
                "partial",
                False,
            ),
        )

        serializer.is_valid(
            raise_exception=True
        )

        zone = serializer.save()

        response_serializer = AddressZoneSerializer(
            zone
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


@admin_ticket_schema_view
class AdminSupportTicketViewSet(
    viewsets.ModelViewSet
):
    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "list": READ_ONLY_ROLES,
        "retrieve": READ_ONLY_ROLES,

        "create": SUPPORT_ROLES,
        "update": SUPPORT_ROLES,
        "partial_update": SUPPORT_ROLES,
        "reply": SUPPORT_ROLES,

        "destroy": ADMIN_ROLES,
    }

    pagination_class = CustomPagination

    filter_backends = [
        DjangoFilterBackend,
    ]

    filterset_fields = [
        "status",
        "priority",
    ]

    def get_queryset(self):
        organization = get_user_organization(
            self.request.user
        )

        return (
            SupportTicket.objects
            .filter(
                customer__organization=organization
            )
            .select_related(
                "customer"
            )
            .prefetch_related(
                "replies__admin_user",
                "replies__customer",
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminSupportTicketDetailSerializer

        return AdminSupportTicketSerializer

    @action(
        detail=True,
        methods=["post"],
    )
    def reply(
        self,
        request,
        pk=None,
    ):
        ticket = self.get_object()

        reply_text = request.data.get(
            "reply_text"
        )

        if not reply_text:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "reply_text field is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reply = TicketReply.objects.create(
            ticket=ticket,
            admin_user=request.user,
            reply_text=reply_text,
        )

        if ticket.status == "open":
            ticket.status = "in_progress"

            ticket.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        serializer = TicketReplySerializer(
            reply
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )