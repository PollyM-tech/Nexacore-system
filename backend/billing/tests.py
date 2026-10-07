from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from auditlog.models import AuditLog
from billing.models import (
    Package,
    PaymentTransaction,
)
from billing.views import (
    BillingViewSet,
    PackageViewSet,
)
from customers.models import (
    AddressZone,
    CustomerProfile,
)
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class BillingRolePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="Billing Test ISP",
            slug="billing-test-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.zone = AddressZone.objects.create(
            organization=self.organization,
            name="Billing Zone",
        )

        self.package = Package.objects.create(
            organization=self.organization,
            name="10 Mbps",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1000.00"),
            is_active=True,
        )

        self.customer = CustomerProfile.objects.create(
            organization=self.organization,
            customer_id="B001",
            customer_name="Billing Customer",
            phone_number="0711000010",
            address="Billing Address",
            zone=self.zone,
            package=self.package,
            customer_status="active",
            balance=Decimal("0.00"),
        )

        self.owner = self._create_user(
            "billing_owner",
            "owner",
        )

        self.admin = self._create_user(
            "billing_admin",
            "admin",
        )

        self.billing = self._create_user(
            "billing_user",
            "billing",
        )

        self.technician = self._create_user(
            "billing_technician",
            "technician",
        )

        self.viewer = self._create_user(
            "billing_viewer",
            "viewer",
        )

    def _create_user(
        self,
        username,
        role,
    ):
        user = User.objects.create_user(
            username=username,
            password="testpass123",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role=role,
            is_active=True,
        )

        return user

    def _request(
        self,
        method,
        path,
        user,
        data=None,
    ):
        method_func = getattr(
            self.factory,
            method.lower(),
        )

        request = method_func(
            path,
            data=data or {},
            format="json",
        )

        force_authenticate(
            request,
            user=user,
        )

        return request

    def test_viewer_can_list_packages(self):
        view = PackageViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/packages/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_technician_cannot_create_package(self):
        view = PackageViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/packages/",
            self.technician,
            {
                "name": "20 Mbps",
                "package_type": "monthly",
                "speed": "20 Mbps",
                "price": "2000.00",
                "description": "",
                "is_active": True,
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            Package.objects.filter(
                organization=self.organization,
                name="20 Mbps",
            ).exists()
        )

    def test_billing_user_can_create_package(self):
        view = PackageViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/packages/",
            self.billing,
            {
                "name": "20 Mbps",
                "package_type": "monthly",
                "speed": "20 Mbps",
                "price": "2000.00",
                "description": (
                    "Billing-created package"
                ),
                "is_active": True,
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            Package.objects.filter(
                organization=self.organization,
                name="20 Mbps",
            ).exists()
        )

    @patch(
        "billing.views."
        "BillingService.create_monthly_bills"
    )
    def test_billing_user_can_generate_monthly_bills(
        self,
        mock_create_bills,
    ):
        mock_create_bills.return_value = []

        view = BillingViewSet.as_view(
            {
                "post": "generate_monthly_bills",
            }
        )

        request = self._request(
            "post",
            "/billing/generate_monthly_bills/",
            self.billing,
            {},
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        mock_create_bills.assert_called_once_with(
            self.organization
        )

    @patch(
        "billing.views."
        "BillingService.create_monthly_bills"
    )
    def test_technician_cannot_generate_monthly_bills(
        self,
        mock_create_bills,
    ):
        view = BillingViewSet.as_view(
            {
                "post": "generate_monthly_bills",
            }
        )

        request = self._request(
            "post",
            "/billing/generate_monthly_bills/",
            self.technician,
            {},
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_create_bills.assert_not_called()

    @patch(
        "billing.views."
        "BillingService.add_payment_transaction"
    )
    def test_billing_user_can_record_payment(
        self,
        mock_add_payment,
    ):
        transaction = PaymentTransaction.objects.create(
            customer=self.customer,
            amount=Decimal("500.00"),
            payment_method="cash",
            transaction_id="TEST123",
            received_by=self.billing,
        )

        mock_add_payment.return_value = transaction

        view = BillingViewSet.as_view(
            {
                "post": "add_transaction",
            }
        )

        request = self._request(
            "post",
            "/billing/add_transaction/",
            self.billing,
            {
                "customer_id": (
                    self.customer.customer_id
                ),
                "amount": "500.00",
                "payment_method": "cash",
                "transaction_id": "TEST123",
                "notes": "Test payment",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        mock_add_payment.assert_called_once()

    @patch(
        "billing.views."
        "BillingService.add_payment_transaction"
    )
    def test_technician_cannot_record_payment(
        self,
        mock_add_payment,
    ):
        view = BillingViewSet.as_view(
            {
                "post": "add_transaction",
            }
        )

        request = self._request(
            "post",
            "/billing/add_transaction/",
            self.technician,
            {
                "customer_id": (
                    self.customer.customer_id
                ),
                "amount": "500.00",
                "payment_method": "cash",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_add_payment.assert_not_called()

    def test_viewer_can_view_monthly_bills(self):
        view = BillingViewSet.as_view(
            {
                "get": "monthly_bills",
            }
        )

        request = self._request(
            "get",
            "/billing/monthly_bills/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )


class BillingAuditLogTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="Billing Audit ISP",
            slug="billing-audit-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.zone = AddressZone.objects.create(
            organization=self.organization,
            name="Audit Zone",
        )

        self.package = Package.objects.create(
            organization=self.organization,
            name="Audit 10 Mbps",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1000.00"),
            is_active=True,
        )

        self.customer = CustomerProfile.objects.create(
            organization=self.organization,
            customer_id="AUD-B001",
            customer_name="Audit Billing Customer",
            phone_number="0711000090",
            address="Audit Billing Address",
            zone=self.zone,
            package=self.package,
            customer_status="active",
            balance=Decimal("0.00"),
        )

        self.billing = User.objects.create_user(
            username="billing_audit_user",
            password="testpass123",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.billing,
            role="billing",
            is_active=True,
        )

    def _request(
        self,
        method,
        path,
        data=None,
    ):
        method_func = getattr(
            self.factory,
            method.lower(),
        )

        request = method_func(
            path,
            data=data or {},
            format="json",
        )

        force_authenticate(
            request,
            user=self.billing,
        )

        return request

    def test_package_creation_creates_audit_log(self):
        view = PackageViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/packages/",
            {
                "name": "Audit 20 Mbps",
                "package_type": "monthly",
                "speed": "20 Mbps",
                "price": "2000.00",
                "description": "",
                "is_active": True,
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        package = Package.objects.get(
            organization=self.organization,
            name="Audit 20 Mbps",
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="package.created",
            resource_id=str(package.pk),
        )

        self.assertEqual(
            log.user,
            self.billing,
        )

        self.assertEqual(
            log.actor_role,
            "billing",
        )

        self.assertEqual(
            log.metadata["price"],
            "2000.00",
        )

    def test_package_toggle_creates_audit_log(self):
        view = PackageViewSet.as_view(
            {
                "patch": "toggle_status",
            }
        )

        request = self._request(
            "patch",
            (
                f"/packages/"
                f"{self.package.pk}/toggle_status/"
            ),
        )

        response = view(
            request,
            pk=self.package.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="package.status_changed",
            resource_id=str(self.package.pk),
        )

        self.assertTrue(
            log.metadata["before"]
        )

        self.assertFalse(
            log.metadata["after"]
        )

    @patch(
        "billing.views."
        "BillingService.create_monthly_bills"
    )
    def test_bulk_bill_generation_creates_audit_log(
        self,
        mock_create_bills,
    ):
        mock_create_bills.return_value = []

        view = BillingViewSet.as_view(
            {
                "post": "generate_monthly_bills",
            }
        )

        request = self._request(
            "post",
            "/billing/generate_monthly_bills/",
            {},
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="billing.monthly_bills_generated",
        )

        self.assertEqual(
            log.user,
            self.billing,
        )

        self.assertEqual(
            log.resource_type,
            "MonthlyBill",
        )

        self.assertEqual(
            log.metadata["bills_created"],
            0,
        )

    @patch(
        "billing.views."
        "BillingService.add_payment_transaction"
    )
    def test_payment_recording_creates_audit_log(
        self,
        mock_add_payment,
    ):
        transaction = PaymentTransaction.objects.create(
            customer=self.customer,
            amount=Decimal("750.00"),
            payment_method="cash",
            transaction_id="AUDPAY01",
            received_by=self.billing,
        )

        mock_add_payment.return_value = transaction

        view = BillingViewSet.as_view(
            {
                "post": "add_transaction",
            }
        )

        request = self._request(
            "post",
            "/billing/add_transaction/",
            {
                "customer_id": (
                    self.customer.customer_id
                ),
                "amount": "750.00",
                "payment_method": "cash",
                "transaction_id": "AUDPAY01",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="billing.payment_recorded",
            resource_id=str(transaction.pk),
        )

        self.assertEqual(
            log.user,
            self.billing,
        )

        self.assertEqual(
            log.metadata["customer_id"],
            self.customer.customer_id,
        )

        self.assertEqual(
            log.metadata["amount"],
            "750.00",
        )

        self.assertEqual(
            log.metadata["payment_method"],
            "cash",
        )