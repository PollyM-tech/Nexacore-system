from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditlog.services import AuditService
from core.pagination import CustomPagination
from organizations.mixins import OrganizationQuerySetMixin
from organizations.permissions import (
    BILLING_ROLES,
    READ_ONLY_ROLES,
    HasOrganizationRole,
)
from organizations.services import get_user_organization

from billing.models import (
    ConnectionFee,
    InvoiceStatusHistory,
    MonthlyBill,
    Package,
    PaymentTransaction,
)

from .filters import (
    ConnectionFeeFilter,
    InvoiceStatusHistoryFilter,
    MonthlyBillFilter,
    PaymentTransactionFilter,
)
from .schemas import package_schema_view
from .schemas.billing_schemas import billing_schema_view
from .serializers import PackageSerializer
from .serializers.invoices import (
    ConnectionFeeCreateSerializer,
    ConnectionFeeSerializer,
    InvoiceStatusHistorySerializer,
    MonthlyBillCreateSerializer,
    MonthlyBillSerializer,
    PaymentTransactionCreateSerializer,
    PaymentTransactionSerializer,
)
from .services import BillingService


@package_schema_view
class PackageViewSet(
    OrganizationQuerySetMixin,
    viewsets.ModelViewSet,
):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer

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
        "toggle_status": BILLING_ROLES,
    }

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]

    search_fields = [
        "name",
        "speed",
        "description",
    ]

    ordering_fields = [
        "price",
        "created_at",
        "name",
        "speed",
    ]

    filterset_fields = [
        "is_active",
    ]

    ordering = [
        "price",
    ]

    pagination_class = CustomPagination

    def perform_create(
        self,
        serializer,
    ):
        organization = self.get_organization()

        package = serializer.save(
            organization=organization
        )

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="package.created",
            resource_type="Package",
            resource_id=package.pk,
            description=(
                f"Package '{package.name}' created."
            ),
            metadata={
                "name": package.name,
                "package_type": package.package_type,
                "speed": package.speed,
                "price": str(package.price),
                "is_active": package.is_active,
            },
        )

    def perform_update(
        self,
        serializer,
    ):
        instance = self.get_object()

        before = {
            "name": instance.name,
            "package_type": instance.package_type,
            "speed": instance.speed,
            "price": str(instance.price),
            "is_active": instance.is_active,
        }

        package = serializer.save()

        after = {
            "name": package.name,
            "package_type": package.package_type,
            "speed": package.speed,
            "price": str(package.price),
            "is_active": package.is_active,
        }

        AuditService.log(
            organization=self.get_organization(),
            user=self.request.user,
            request=self.request,
            action="package.updated",
            resource_type="Package",
            resource_id=package.pk,
            description=(
                f"Package '{package.name}' updated."
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
        package_name = instance.name

        metadata = {
            "name": instance.name,
            "package_type": instance.package_type,
            "speed": instance.speed,
            "price": str(instance.price),
            "is_active": instance.is_active,
        }

        instance.delete()

        AuditService.log(
            organization=organization,
            user=self.request.user,
            request=self.request,
            action="package.deleted",
            resource_type="Package",
            resource_id=resource_id,
            description=(
                f"Package '{package_name}' deleted."
            ),
            metadata=metadata,
        )

    @action(
        detail=True,
        methods=["patch"],
    )
    def toggle_status(
        self,
        request,
        pk=None,
    ):
        package = self.get_object()

        old_status = package.is_active

        package.is_active = not package.is_active

        package.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        AuditService.log(
            organization=self.get_organization(),
            user=request.user,
            request=request,
            action="package.status_changed",
            resource_type="Package",
            resource_id=package.pk,
            description=(
                f"Package '{package.name}' "
                f"{'enabled' if package.is_active else 'disabled'}."
            ),
            metadata={
                "before": old_status,
                "after": package.is_active,
            },
        )

        serializer = self.get_serializer(
            package
        )

        return Response(
            serializer.data
        )


@billing_schema_view
class BillingViewSet(viewsets.ViewSet):
    permission_classes = [
        IsAuthenticated,
        HasOrganizationRole,
    ]

    role_permissions = {
        "generate_monthly_bills": BILLING_ROLES,
        "generate_customer_monthly_bill": BILLING_ROLES,
        "generate_connection_fee": BILLING_ROLES,
        "add_transaction": BILLING_ROLES,

        "monthly_bills": READ_ONLY_ROLES,
        "connection_fees": READ_ONLY_ROLES,
        "transactions": READ_ONLY_ROLES,
        "status_histories": READ_ONLY_ROLES,
    }

    def get_organization(self):
        return get_user_organization(
            self.request.user
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def generate_monthly_bills(
        self,
        request,
    ):
        organization = self.get_organization()

        billing_month = request.data.get(
            "billing_month"
        )

        billing_year = request.data.get(
            "billing_year"
        )

        if billing_month and billing_year:
            created = BillingService.create_monthly_bills(
                organization,
                int(billing_month),
                int(billing_year),
            )
        else:
            created = BillingService.create_monthly_bills(
                organization
            )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="billing.monthly_bills_generated",
            resource_type="MonthlyBill",
            resource_id="bulk",
            description=(
                f"Generated {len(created)} monthly bills."
            ),
            metadata={
                "billing_month": (
                    int(billing_month)
                    if billing_month
                    else None
                ),
                "billing_year": (
                    int(billing_year)
                    if billing_year
                    else None
                ),
                "bills_created": len(created),
            },
        )

        return Response(
            {
                "status": "success",
                "message": (
                    f"Created {len(created)} monthly bills"
                ),
                "bills_created": len(created),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def generate_customer_monthly_bill(
        self,
        request,
    ):
        organization = self.get_organization()

        serializer = MonthlyBillCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer_id = serializer.validated_data[
            "customer_id"
        ]

        billing_month = serializer.validated_data[
            "billing_month"
        ]

        billing_year = serializer.validated_data[
            "billing_year"
        ]

        notes = serializer.validated_data.get(
            "notes",
            "",
        )

        result = BillingService.create_specific_monthly_bill(
            organization,
            customer_id,
            billing_month,
            billing_year,
            notes,
        )

        if result["status"] == "error":
            return Response(
                {
                    "status": "error",
                    "message": result["message"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bill = result["bill"]

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="billing.monthly_bill_generated",
            resource_type="MonthlyBill",
            resource_id=bill.pk,
            description=(
                f"Monthly bill generated for "
                f"customer '{customer_id}'."
            ),
            metadata={
                "customer_id": customer_id,
                "billing_month": billing_month,
                "billing_year": billing_year,
                "total_amount": str(
                    bill.total_amount
                ),
            },
        )

        response_serializer = MonthlyBillSerializer(
            bill
        )

        return Response(
            {
                "status": "success",
                "message": result["message"],
                "bill": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def generate_connection_fee(
        self,
        request,
    ):
        organization = self.get_organization()

        serializer = ConnectionFeeCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer_id = serializer.validated_data[
            "customer_id"
        ]

        total_amount = serializer.validated_data[
            "total_amount"
        ]

        notes = serializer.validated_data.get(
            "notes",
            "",
        )

        result = BillingService.create_connection_fee(
            organization,
            customer_id,
            total_amount,
            notes,
        )

        if result["status"] == "error":
            return Response(
                {
                    "status": "error",
                    "message": result["message"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        fee = result["fee"]

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="billing.connection_fee_generated",
            resource_type="ConnectionFee",
            resource_id=fee.pk,
            description=(
                f"Connection fee created for "
                f"customer '{customer_id}'."
            ),
            metadata={
                "customer_id": customer_id,
                "total_amount": str(
                    total_amount
                ),
            },
        )

        response_serializer = ConnectionFeeSerializer(
            fee
        )

        return Response(
            {
                "status": "success",
                "message": result["message"],
                "fee": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def monthly_bills(
        self,
        request,
    ):
        organization = self.get_organization()

        bills = (
            MonthlyBill.objects
            .filter(
                customer__organization=organization
            )
            .select_related(
                "customer"
            )
        )

        filterset = MonthlyBillFilter(
            request.query_params,
            queryset=bills,
        )

        if filterset.is_valid():
            bills = filterset.qs

        paginator = CustomPagination()

        page = paginator.paginate_queryset(
            bills,
            request,
            view=self,
        )

        if page is not None:
            serializer = MonthlyBillSerializer(
                page,
                many=True,
            )

            return paginator.get_paginated_response(
                serializer.data
            )

        serializer = MonthlyBillSerializer(
            bills,
            many=True,
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
        organization = self.get_organization()

        fees = (
            ConnectionFee.objects
            .filter(
                customer__organization=organization
            )
            .select_related(
                "customer"
            )
        )

        filterset = ConnectionFeeFilter(
            request.query_params,
            queryset=fees,
        )

        if filterset.is_valid():
            fees = filterset.qs

        paginator = CustomPagination()

        page = paginator.paginate_queryset(
            fees,
            request,
            view=self,
        )

        if page is not None:
            serializer = ConnectionFeeSerializer(
                page,
                many=True,
            )

            return paginator.get_paginated_response(
                serializer.data
            )

        serializer = ConnectionFeeSerializer(
            fees,
            many=True,
        )

        return Response(
            serializer.data
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def add_transaction(
        self,
        request,
    ):
        organization = self.get_organization()

        serializer = PaymentTransactionCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        customer_id = serializer.validated_data[
            "customer_id"
        ]

        amount = serializer.validated_data[
            "amount"
        ]

        payment_method = serializer.validated_data[
            "payment_method"
        ]

        transaction_id = (
            serializer.validated_data.get(
                "transaction_id"
            )
        )

        notes = serializer.validated_data.get(
            "notes",
            "",
        )

        transaction_obj = (
            BillingService.add_payment_transaction(
                organization=organization,
                customer_id=customer_id,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id,
                received_by=request.user,
                notes=notes,
            )
        )

        AuditService.log(
            organization=organization,
            user=request.user,
            request=request,
            action="billing.payment_recorded",
            resource_type="PaymentTransaction",
            resource_id=transaction_obj.pk,
            description=(
                f"Payment of {amount} recorded for "
                f"customer '{customer_id}'."
            ),
            metadata={
                "customer_id": customer_id,
                "amount": str(amount),
                "payment_method": payment_method,
                "transaction_id": (
                    transaction_id or ""
                ),
            },
        )

        response_serializer = (
            PaymentTransactionSerializer(
                transaction_obj
            )
        )

        return Response(
            {
                "status": "success",
                "message": (
                    "Payment transaction recorded "
                    "and allocated successfully."
                ),
                "transaction": (
                    response_serializer.data
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def transactions(
        self,
        request,
    ):
        organization = self.get_organization()

        transactions = (
            PaymentTransaction.objects
            .filter(
                customer__organization=organization
            )
            .select_related(
                "customer",
                "received_by",
            )
        )

        filterset = PaymentTransactionFilter(
            request.query_params,
            queryset=transactions,
        )

        if filterset.is_valid():
            transactions = filterset.qs

        paginator = CustomPagination()

        page = paginator.paginate_queryset(
            transactions,
            request,
            view=self,
        )

        if page is not None:
            serializer = PaymentTransactionSerializer(
                page,
                many=True,
            )

            return paginator.get_paginated_response(
                serializer.data
            )

        serializer = PaymentTransactionSerializer(
            transactions,
            many=True,
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
        organization = self.get_organization()

        histories = (
            InvoiceStatusHistory.objects
            .filter(
                Q(
                    monthly_bill__customer__organization=
                    organization
                )
                | Q(
                    connection_fee__customer__organization=
                    organization
                )
                | Q(
                    payment_transaction__customer__organization=
                    organization
                )
            )
            .distinct()
            .select_related(
                "monthly_bill__customer",
                "connection_fee__customer",
                "payment_transaction",
            )
        )

        filterset = InvoiceStatusHistoryFilter(
            request.query_params,
            queryset=histories,
        )

        if filterset.is_valid():
            histories = filterset.qs

        paginator = CustomPagination()

        page = paginator.paginate_queryset(
            histories,
            request,
            view=self,
        )

        if page is not None:
            serializer = InvoiceStatusHistorySerializer(
                page,
                many=True,
            )

            return paginator.get_paginated_response(
                serializer.data
            )

        serializer = InvoiceStatusHistorySerializer(
            histories,
            many=True,
        )

        return Response(
            serializer.data
        )