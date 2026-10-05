from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

from billing.models import MonthlyBill, Package
from billing.views import BillingViewSet, PackageViewSet
from customers.models import AddressZone, CustomerProfile
from customers.views import CustomerViewSet
from mikrotik.models import MikrotikRouter
from mikrotik.views import MikrotikRouterViewSet
from organizations.models import Organization, OrganizationMembership


User = get_user_model()


class TenantIsolationTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        # Organization A
        self.org_a = Organization.objects.create(
            name="ISP Alpha",
            slug="isp-alpha",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        # Organization B
        self.org_b = Organization.objects.create(
            name="ISP Beta",
            slug="isp-beta",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        # Staff user for Organization A
        self.user_a = User.objects.create_user(
            username="alpha-admin",
            email="alpha@example.com",
            password="test-password-123",
        )

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role="owner",
            is_active=True,
        )

        # Staff user for Organization B
        self.user_b = User.objects.create_user(
            username="beta-admin",
            email="beta@example.com",
            password="test-password-123",
        )

        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role="owner",
            is_active=True,
        )

        # Zones
        self.zone_a = AddressZone.objects.create(
            organization=self.org_a,
            name="Alpha Zone",
        )

        self.zone_b = AddressZone.objects.create(
            organization=self.org_b,
            name="Beta Zone",
        )

        # Packages
        self.package_a = Package.objects.create(
            organization=self.org_a,
            name="Alpha 10 Mbps",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1500.00"),
            is_active=True,
        )

        self.package_b = Package.objects.create(
            organization=self.org_b,
            name="Beta 20 Mbps",
            package_type="monthly",
            speed="20 Mbps",
            price=Decimal("2500.00"),
            is_active=True,
        )

        # Customers
        self.customer_a = CustomerProfile.objects.create(
            organization=self.org_a,
            customer_id="100001",
            customer_name="Alpha Customer",
            phone_number="0711111111",
            address="Alpha Estate",
            zone=self.zone_a,
            package=self.package_a,
            customer_status="active",
            balance=Decimal("0.00"),
        )

        self.customer_b = CustomerProfile.objects.create(
            organization=self.org_b,
            customer_id="200001",
            customer_name="Beta Customer",
            phone_number="0722222222",
            address="Beta Estate",
            zone=self.zone_b,
            package=self.package_b,
            customer_status="active",
            balance=Decimal("0.00"),
        )

        # Routers
        self.router_a = MikrotikRouter.objects.create(
            organization=self.org_a,
            name="Alpha Router",
            host="10.10.10.1",
            port=8728,
            username="admin",
            password="alpha-password",
            status="disconnected",
            is_active=True,
        )

        self.router_b = MikrotikRouter.objects.create(
            organization=self.org_b,
            name="Beta Router",
            host="10.20.20.1",
            port=8728,
            username="admin",
            password="beta-password",
            status="disconnected",
            is_active=True,
        )

        # Bills
        self.bill_a = MonthlyBill.objects.create(
            customer=self.customer_a,
            package_name=self.package_a.name,
            package_price=self.package_a.price,
            billing_month=10,
            billing_year=2026,
            invoice_date="2026-10-01",
            total_amount=Decimal("1500.00"),
            paid_amount=Decimal("0.00"),
        )

        self.bill_b = MonthlyBill.objects.create(
            customer=self.customer_b,
            package_name=self.package_b.name,
            package_price=self.package_b.price,
            billing_month=10,
            billing_year=2026,
            invoice_date="2026-10-01",
            total_amount=Decimal("2500.00"),
            paid_amount=Decimal("0.00"),
        )

    def authenticate(self, request, user=None):
        force_authenticate(
            request,
            user=user or self.user_a,
        )
        return request

    def extract_results(self, response):
        """
        Support both paginated and non-paginated DRF responses.
        """
        data = response.data

        if isinstance(data, dict) and "results" in data:
            return data["results"]

        return data

    def test_customer_list_only_returns_current_organization(self):
        view = CustomerViewSet.as_view({
            "get": "list",
        })

        request = self.factory.get("/customers/")
        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = self.extract_results(response)

        customer_ids = [
            item["customer_id"]
            for item in results
        ]

        self.assertIn(
            self.customer_a.customer_id,
            customer_ids,
        )

        self.assertNotIn(
            self.customer_b.customer_id,
            customer_ids,
        )

    def test_user_cannot_retrieve_other_organization_customer(self):
        view = CustomerViewSet.as_view({
            "get": "retrieve",
        })

        request = self.factory.get(
            f"/customers/{self.customer_b.customer_id}/"
        )

        self.authenticate(request)

        response = view(
            request,
            customer_id=self.customer_b.customer_id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_package_list_is_tenant_scoped(self):
        view = PackageViewSet.as_view({
            "get": "list",
        })

        request = self.factory.get("/packages/")
        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = self.extract_results(response)

        package_names = [
            item["name"]
            for item in results
        ]

        self.assertIn(
            self.package_a.name,
            package_names,
        )

        self.assertNotIn(
            self.package_b.name,
            package_names,
        )

    def test_router_list_is_tenant_scoped(self):
        view = MikrotikRouterViewSet.as_view({
            "get": "list",
        })

        request = self.factory.get("/routers/")
        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = self.extract_results(response)

        router_names = [
            item["name"]
            for item in results
        ]

        self.assertIn(
            self.router_a.name,
            router_names,
        )

        self.assertNotIn(
            self.router_b.name,
            router_names,
        )

    def test_monthly_bill_list_is_tenant_scoped(self):
        view = BillingViewSet.as_view({
            "get": "monthly_bills",
        })

        request = self.factory.get(
            "/billing/monthly-bills/"
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = self.extract_results(response)

        bill_ids = [
            item["id"]
            for item in results
        ]

        self.assertIn(
            self.bill_a.id,
            bill_ids,
        )

        self.assertNotIn(
            self.bill_b.id,
            bill_ids,
        )

    def test_user_cannot_pay_other_organization_customer(self):
        view = BillingViewSet.as_view({
            "post": "add_transaction",
        })

        request = self.factory.post(
            "/billing/add-transaction/",
            {
                "customer_id": self.customer_b.customer_id,
                "amount": "500.00",
                "payment_method": "cash",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.customer_b.refresh_from_db()

        self.assertEqual(
            self.customer_b.balance,
            Decimal("0.00"),
        )

    def test_user_can_access_own_organization_customer(self):
        view = CustomerViewSet.as_view({
            "get": "retrieve",
        })

        request = self.factory.get(
            f"/customers/{self.customer_a.customer_id}/"
        )

        self.authenticate(request)

        response = view(
            request,
            customer_id=self.customer_a.customer_id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["customer_id"],
            self.customer_a.customer_id,
        )

    def test_second_organization_has_separate_visibility(self):
        view = CustomerViewSet.as_view({
            "get": "list",
        })

        request = self.factory.get("/customers/")
        self.authenticate(
            request,
            user=self.user_b,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = self.extract_results(response)

        customer_ids = [
            item["customer_id"]
            for item in results
        ]

        self.assertIn(
            self.customer_b.customer_id,
            customer_ids,
        )

        self.assertNotIn(
            self.customer_a.customer_id,
            customer_ids,
        )