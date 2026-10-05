from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import (
    MonthlyBill,
    Package,
    PaymentTransaction,
)
from customers.models import (
    AddressZone,
    CustomerProfile,
    SupportTicket,
)
from mikrotik.models import MikrotikRouter
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class ReportTenantIsolationTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="ISP A",
            slug="isp-a",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.org_b = Organization.objects.create(
            name="ISP B",
            slug="isp-b",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.user_a = User.objects.create_user(
            username="admin_a",
            password="testpass123",
        )

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role="owner",
            is_active=True,
        )

        self.zone_a = AddressZone.objects.create(
            organization=self.org_a,
            name="Zone A",
        )

        self.zone_b = AddressZone.objects.create(
            organization=self.org_b,
            name="Zone B",
        )

        self.package_a = Package.objects.create(
            organization=self.org_a,
            name="Package A",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1000.00"),
            is_active=True,
        )

        self.package_b = Package.objects.create(
            organization=self.org_b,
            name="Package B",
            package_type="monthly",
            speed="20 Mbps",
            price=Decimal("2000.00"),
            is_active=True,
        )

        self.customer_a = CustomerProfile.objects.create(
            organization=self.org_a,
            customer_id="A001",
            customer_name="Customer A",
            phone_number="0711000001",
            address="Test Address A",
            zone=self.zone_a,
            package=self.package_a,
            customer_status="active",
            balance=Decimal("-200.00"),
        )

        self.customer_b = CustomerProfile.objects.create(
            organization=self.org_b,
            customer_id="B001",
            customer_name="Customer B",
            phone_number="0711000002",
            address="Test Address B",
            zone=self.zone_b,
            package=self.package_b,
            customer_status="active",
            balance=Decimal("-500.00"),
        )

        self.router_a = MikrotikRouter.objects.create(
            organization=self.org_a,
            name="Router A",
            host="10.0.0.1",
            port=8728,
            username="admin",
            password="password",
            is_active=True,
        )

        self.router_b = MikrotikRouter.objects.create(
            organization=self.org_b,
            name="Router B",
            host="10.0.0.2",
            port=8728,
            username="admin",
            password="password",
            is_active=True,
        )

        SupportTicket.objects.create(
            customer=self.customer_a,
            title="Ticket A",
            description="ISP A issue",
            status="open",
        )

        SupportTicket.objects.create(
            customer=self.customer_b,
            title="Ticket B",
            description="ISP B issue",
            status="resolved",
        )

        MonthlyBill.objects.create(
            customer=self.customer_a,
            package_name=self.package_a.name,
            package_price=self.package_a.price,
            billing_month=date.today().month,
            billing_year=date.today().year,
            invoice_date=date.today(),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
            payment_status="partial",
        )

        MonthlyBill.objects.create(
            customer=self.customer_b,
            package_name=self.package_b.name,
            package_price=self.package_b.price,
            billing_month=date.today().month,
            billing_year=date.today().year,
            invoice_date=date.today(),
            total_amount=Decimal("5000.00"),
            paid_amount=Decimal("5000.00"),
            payment_status="paid",
        )

        PaymentTransaction.objects.create(
            customer=self.customer_a,
            amount=Decimal("400.00"),
            payment_method="cash",
        )

        PaymentTransaction.objects.create(
            customer=self.customer_b,
            amount=Decimal("5000.00"),
            payment_method="cash",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user_a)

    def test_dashboard_only_counts_current_organization_customers(self):
        response = self.client.get("/api/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["customers"]["total"],
            1,
        )
        self.assertEqual(
            response.data["customers"]["active"],
            1,
        )
        self.assertEqual(
            response.data["customers"]["due"],
            1,
        )

    def test_dashboard_only_counts_current_organization_packages(self):
        response = self.client.get("/api/reports/dashboard/")

        self.assertEqual(
            response.data["packages"]["total"],
            1,
        )
        self.assertEqual(
            response.data["packages"]["active"],
            1,
        )

    def test_dashboard_only_counts_current_organization_routers(self):
        response = self.client.get("/api/reports/dashboard/")

        self.assertEqual(
            response.data["routers"]["total"],
            1,
        )
        self.assertEqual(
            response.data["routers"]["active"],
            1,
        )

    def test_dashboard_only_counts_current_organization_tickets(self):
        response = self.client.get("/api/reports/dashboard/")

        self.assertEqual(
            response.data["tickets"]["total"],
            1,
        )
        self.assertEqual(
            response.data["tickets"]["open"],
            1,
        )
        self.assertEqual(
            response.data["tickets"]["resolved"],
            0,
        )

    def test_dashboard_revenue_excludes_other_organizations(self):
        response = self.client.get("/api/reports/dashboard/")

        revenue = response.data["revenue"]

        self.assertEqual(
            revenue["billed"],
            1000.0,
        )
        self.assertEqual(
            revenue["collected"],
            400.0,
        )
        self.assertEqual(
            revenue["outstanding"],
            600.0,
        )
        self.assertEqual(
            revenue["collection_rate"],
            40,
        )

    def test_dashboard_today_revenue_excludes_other_organizations(self):
        response = self.client.get("/api/reports/dashboard/")

        self.assertEqual(
            response.data["revenue"]["today"],
            400.0,
        )

    def test_monthly_report_excludes_other_organizations(self):
        response = self.client.get("/api/reports/dashboard/")

        current_month = date.today().month

        row = next(
            item
            for item in response.data["monthly"]
            if item["month"] == current_month
        )

        self.assertEqual(
            row["billed"],
            1000.0,
        )
        self.assertEqual(
            row["collected"],
            400.0,
        )
        self.assertEqual(
            row["due"],
            600.0,
        )

    def test_yearly_report_excludes_other_organizations(self):
        response = self.client.get("/api/reports/dashboard/")

        current_year = date.today().year

        row = next(
            item
            for item in response.data["yearly"]
            if item["year"] == current_year
        )

        self.assertEqual(
            row["billed"],
            1000.0,
        )
        self.assertEqual(
            row["collected"],
            400.0,
        )