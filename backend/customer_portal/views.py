from datetime import timedelta
from secrets import compare_digest

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from billing.models import (
    ConnectionFee,
    InvoiceStatusHistory,
    MonthlyBill,
    Package,
    PaymentTransaction,
)
from core.pagination import CustomPagination
from customers.models import (
    CustomerProfile,
    SupportTicket,
    TicketReply,
)
from customers.serializers.tickets import (
    TicketReplySerializer,
)
from mikrotik.models import RouterInfo
from organizations.models import Organization

from .authentication import (
    CustomerPortalAuthentication,
    IsAuthenticatedCustomer,
)
from .models import CustomerToken
from .schemas import (
    portal_schema_view,
    portal_ticket_schema_view,
)
from .serializers import (
    CustomerPortalLoginSerializer,
    CustomerPortalProfileSerializer,
    PortalConnectionFeeSerializer,
    PortalInvoiceStatusHistorySerializer,
    PortalMonthlyBillSerializer,
    PortalPaymentTransactionSerializer,
    PortalSupportTicketDetailSerializer,
    PortalSupportTicketSerializer,
    PublicPackageSerializer,
)


@extend_schema(tags=["customer_portal"])
class PublicPackageViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Publicly list active packages for one organization.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicPackageSerializer
    pagination_class = None

    def get_queryset(self):
        organization_slug = (
            self.request.query_params.get(
                "organization"
            )
        )

        if not organization_slug:
            return Package.objects.none()

        return Package.objects.filter(
            organization__slug=organization_slug,
            organization__is_active=True,
            is_active=True,
        )


@portal_schema_view
class AuthViewSet(viewsets.ViewSet):
    """
    Customer portal authentication and profile operations.
    """

    @action(
        detail=False,
        methods=["post"],
    )
    def login(self, request):
        serializer = CustomerPortalLoginSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        organization_slug = (
            serializer.validated_data[
                "organization"
            ]
        )

        username = (
            serializer.validated_data[
                "pppoe_name"
            ]
            .strip()
            .lower()
        )

        password = (
            serializer.validated_data[
                "pppoe_pass"
            ]
        )

        organization = (
            Organization.objects
            .filter(
                slug=organization_slug,
                is_active=True,
            )
            .first()
        )

        if organization is None:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Invalid organization "
                        "or credentials."
                    ),
                },
                status=(
                    status.HTTP_401_UNAUTHORIZED
                ),
            )

        #
        # IMPORTANT:
        #
        # pppoe_pass is encrypted at rest using Fernet.
        # Fernet encryption is randomized, so encrypted
        # values cannot be queried with:
        #
        #     pppoe_pass=password
        #
        # Query only by tenant + PPPoE username.
        # Django decrypts pppoe_pass when each RouterInfo
        # object is loaded, then we compare the submitted
        # password in Python.
        #
        candidates = (
            RouterInfo.objects
            .select_related(
                "customer",
                "customer__organization",
            )
            .filter(
                customer__organization=organization,
                pppoe_name__iexact=username,
            )
        )

        router_info = None

        for candidate in candidates:
            stored_password = (
                candidate.pppoe_pass or ""
            )

            if compare_digest(
                stored_password,
                password,
            ):
                router_info = candidate
                break

        if router_info is None:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Invalid organization "
                        "or credentials."
                    ),
                },
                status=(
                    status.HTTP_401_UNAUTHORIZED
                ),
            )

        customer = router_info.customer

        if (
            customer.customer_status
            != "active"
        ):
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Customer profile "
                        "is deactivated."
                    ),
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )

        CustomerToken.objects.filter(
            customer=customer,
            expires_at__lt=timezone.now(),
        ).delete()

        token = CustomerToken.objects.create(
            customer=customer,
            expires_at=(
                timezone.now()
                + timedelta(days=7)
            ),
        )

        return Response(
            {
                "status": "success",
                "token": token.key,
                "expires_at": (
                    token.expires_at
                ),
                "customer_name": (
                    customer.customer_name
                ),
                "customer_id": (
                    customer.customer_id
                ),
                "organization": (
                    organization.slug
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        authentication_classes=[
            CustomerPortalAuthentication
        ],
        permission_classes=[
            IsAuthenticatedCustomer
        ],
    )
    def profile(self, request):
        serializer = (
            CustomerPortalProfileSerializer(
                request.user
            )
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["post"],
        authentication_classes=[
            CustomerPortalAuthentication
        ],
        permission_classes=[
            IsAuthenticatedCustomer
        ],
    )
    def logout(self, request):
        token = request.auth

        token.is_active = False
        token.save(
            update_fields=[
                "is_active"
            ]
        )

        return Response(
            {
                "status": "success",
                "message": (
                    "Logged out successfully."
                ),
            }
        )


@portal_schema_view
class DashboardViewSet(
    viewsets.ViewSet
):
    authentication_classes = [
        CustomerPortalAuthentication
    ]

    permission_classes = [
        IsAuthenticatedCustomer
    ]

    @action(
        detail=False,
        methods=["get"],
    )
    def stats(self, request):
        customer = request.user

        try:
            router_info = (
                customer.router_info
            )

            router = (
                router_info.router
            )

        except RouterInfo.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Router configuration "
                        "not found."
                    ),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        if not router:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Router connection info "
                        "not assigned."
                    ),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        if (
            router.organization_id
            != customer.organization_id
        ):
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Router organization "
                        "mismatch."
                    ),
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )

        from mikrotik.service.connection import (
            MikrotikConnection,
        )

        try:
            conn = MikrotikConnection(
                host=router.host,
                port=router.port,
                username=router.username,
                password=router.password,
            )

            if not conn.api:
                return Response(
                    {
                        "status": "offline",
                        "message": (
                            "Unable to connect "
                            "to router to fetch "
                            "live stats."
                        ),
                        "live_stats_available": (
                            False
                        ),
                    }
                )

            active_resource = (
                conn.api.get_resource(
                    "/ppp/active"
                )
            )

            active = active_resource.get(
                name=(
                    router_info
                    .pppoe_name
                    .lower()
                )
            )

            if active:
                stats_data = active[0]

                return Response(
                    {
                        "status": "online",
                        "live_stats_available": (
                            True
                        ),
                        "uptime": (
                            stats_data.get(
                                "uptime",
                                "unknown",
                            )
                        ),
                        "bytes_in": (
                            stats_data.get(
                                "bytes-in",
                                "0",
                            )
                        ),
                        "bytes_out": (
                            stats_data.get(
                                "bytes-out",
                                "0",
                            )
                        ),
                        "caller_id": (
                            stats_data.get(
                                "caller-id",
                                "unknown",
                            )
                        ),
                        "address": (
                            stats_data.get(
                                "address",
                                "unknown",
                            )
                        ),
                    }
                )

            secret_resource = (
                conn.api.get_resource(
                    "/ppp/secret"
                )
            )

            secret = secret_resource.get(
                name=(
                    router_info
                    .pppoe_name
                    .lower()
                )
            )

            last_caller = "unknown"
            last_disconnect = "unknown"

            if secret:
                last_caller = (
                    secret[0].get(
                        "last-caller",
                        "unknown",
                    )
                )

                last_disconnect = (
                    secret[0].get(
                        (
                            "last-disconnect-"
                            "reason"
                        ),
                        "unknown",
                    )
                )

            return Response(
                {
                    "status": "offline",
                    "live_stats_available": (
                        False
                    ),
                    "last_caller": (
                        last_caller
                    ),
                    (
                        "last_disconnect_reason"
                    ): last_disconnect,
                }
            )

        except Exception as exc:
            return Response(
                {
                    "status": "offline",
                    "message": (
                        "Router stats "
                        "retrieval error: "
                        f"{str(exc)}"
                    ),
                    "live_stats_available": (
                        False
                    ),
                }
            )


@portal_schema_view
class BillingViewSet(
    viewsets.ViewSet
):
    authentication_classes = [
        CustomerPortalAuthentication
    ]

    permission_classes = [
        IsAuthenticatedCustomer
    ]

    @action(
        detail=False,
        methods=["get"],
    )
    def monthly_bills(self, request):
        bills = (
            MonthlyBill.objects.filter(
                customer=request.user
            )
        )

        paginator = CustomPagination()

        page = (
            paginator.paginate_queryset(
                bills,
                request,
                view=self,
            )
        )

        if page is not None:
            serializer = (
                PortalMonthlyBillSerializer(
                    page,
                    many=True,
                )
            )

            return (
                paginator
                .get_paginated_response(
                    serializer.data
                )
            )

        serializer = (
            PortalMonthlyBillSerializer(
                bills,
                many=True,
            )
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def connection_fees(
        self,
        request,
    ):
        fees = (
            ConnectionFee.objects.filter(
                customer=request.user
            )
        )

        paginator = CustomPagination()

        page = (
            paginator.paginate_queryset(
                fees,
                request,
                view=self,
            )
        )

        if page is not None:
            serializer = (
                PortalConnectionFeeSerializer(
                    page,
                    many=True,
                )
            )

            return (
                paginator
                .get_paginated_response(
                    serializer.data
                )
            )

        serializer = (
            PortalConnectionFeeSerializer(
                fees,
                many=True,
            )
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def transactions(
        self,
        request,
    ):
        txs = (
            PaymentTransaction.objects
            .filter(
                customer=request.user
            )
        )

        paginator = CustomPagination()

        page = (
            paginator.paginate_queryset(
                txs,
                request,
                view=self,
            )
        )

        if page is not None:
            serializer = (
                PortalPaymentTransactionSerializer(
                    page,
                    many=True,
                )
            )

            return (
                paginator
                .get_paginated_response(
                    serializer.data
                )
            )

        serializer = (
            PortalPaymentTransactionSerializer(
                txs,
                many=True,
            )
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def status_histories(
        self,
        request,
    ):
        histories = (
            InvoiceStatusHistory.objects
            .filter(
                Q(
                    monthly_bill__customer=(
                        request.user
                    )
                )
                |
                Q(
                    connection_fee__customer=(
                        request.user
                    )
                )
            )
            .select_related(
                "payment_transaction"
            )
        )

        paginator = CustomPagination()

        page = (
            paginator.paginate_queryset(
                histories,
                request,
                view=self,
            )
        )

        if page is not None:
            serializer = (
                PortalInvoiceStatusHistorySerializer(
                    page,
                    many=True,
                )
            )

            return (
                paginator
                .get_paginated_response(
                    serializer.data
                )
            )

        serializer = (
            PortalInvoiceStatusHistorySerializer(
                histories,
                many=True,
            )
        )

        return Response(
            serializer.data
        )


@portal_ticket_schema_view
class SupportTicketViewSet(
    viewsets.ModelViewSet
):
    serializer_class = (
        PortalSupportTicketSerializer
    )

    authentication_classes = [
        CustomerPortalAuthentication
    ]

    permission_classes = [
        IsAuthenticatedCustomer
    ]

    queryset = (
        SupportTicket.objects.all()
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return (
                PortalSupportTicketDetailSerializer
            )

        return (
            PortalSupportTicketSerializer
        )

    def get_queryset(self):
        return (
            SupportTicket.objects.filter(
                customer=self.request.user
            )
        )

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

        reply_text = (
            request.data.get(
                "reply_text"
            )
        )

        if not reply_text:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "reply_text field "
                        "is required."
                    ),
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        reply = (
            TicketReply.objects.create(
                ticket=ticket,
                customer=request.user,
                reply_text=reply_text,
            )
        )

        if ticket.status == "closed":
            ticket.status = "open"

            ticket.save(
                update_fields=[
                    "status"
                ]
            )

        serializer = (
            TicketReplySerializer(
                reply
            )
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_201_CREATED
            ),
        )