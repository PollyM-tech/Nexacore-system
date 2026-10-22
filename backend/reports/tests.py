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
        self.client.force_authenticate(
            self.user_a
        )

    def test_dashboard_only_counts_current_organization_customers(self):
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

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
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        self.assertEqual(
            response.data["packages"]["total"],
            1,
        )

        self.assertEqual(
            response.data["packages"]["active"],
            1,
        )

    def test_dashboard_only_counts_current_organization_routers(self):
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        self.assertEqual(
            response.data["routers"]["total"],
            1,
        )

        self.assertEqual(
            response.data["routers"]["active"],
            1,
        )

    def test_dashboard_only_counts_current_organization_tickets(self):
        response = self.client.get(
            "/api/reports/dashboard/"
        )

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
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        revenue = response.data[
            "revenue"
        ]

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
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        self.assertEqual(
            response.data["revenue"]["today"],
            400.0,
        )

    def test_monthly_report_excludes_other_organizations(self):
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        current_month = (
            date.today().month
        )

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
        response = self.client.get(
            "/api/reports/dashboard/"
        )

        current_year = (
            date.today().year
        )

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


class ReportRolePermissionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Report Role Test ISP",
            slug="report-role-test-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.viewer = self._create_user(
            "report_viewer",
            "viewer",
        )

        self.technician = self._create_user(
            "report_technician",
            "technician",
        )

        self.billing = self._create_user(
            "report_billing",
            "billing",
        )

        self.support = self._create_user(
            "report_support",
            "support",
        )

        self.client = APIClient()

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

    def _assert_can_view_report(
        self,
        user,
    ):
        self.client.force_authenticate(
            user
        )

        response = self.client.get(
            "/api/reports/dashboard/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_viewer_can_view_report(self):
        self._assert_can_view_report(
            self.viewer
        )

    def test_technician_can_view_report(self):
        self._assert_can_view_report(
            self.technician
        )

    def test_billing_user_can_view_report(self):
        self._assert_can_view_report(
            self.billing
        )

    def test_support_user_can_view_report(self):
        self._assert_can_view_report(
            self.support
        )

class ReportReceivedIncomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Receipts", slug="receipts", is_active=True)
        cls.other = Organization.objects.create(name="Other", slug="other", is_active=True)
        cls.user = User.objects.create_user(username="receipts-admin")
        OrganizationMembership.objects.create(organization=cls.org, user=cls.user, role="owner", is_active=True)
        cls.customers = []
        for org in (cls.org, cls.other):
            zone = AddressZone.objects.create(organization=org, name="Zone")
            cls.customers.append(CustomerProfile.objects.create(
                organization=org, customer_id="R1", customer_name="Receipt customer",
                phone_number="0711000000", address="Test", zone=zone,
            ))

    def setUp(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo
        from django.utils import timezone
        # Wednesday just after Nairobi midnight, still Tuesday in UTC.
        self.now = datetime(2026, 10, 14, 0, 30, tzinfo=ZoneInfo("Africa/Nairobi"))
        override = timezone.override(self.now.tzinfo)
        override.__enter__()
        self.addCleanup(override.__exit__, None, None, None)
        clock = patch("reports.services.timezone.now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payment(self, amount="100.25", method="cash", at=None, other=False):
        row = PaymentTransaction.objects.create(
            customer=self.customers[int(other)], amount=Decimal(amount), payment_method=method,
        )
        PaymentTransaction.objects.filter(pk=row.pk).update(created_at=at or self.now)

    def received(self):
        response = self.client.get("/api/reports/dashboard/")
        self.assertEqual(response.status_code, 200)
        return response.json()["revenue"]["received"]

    def test_today_positive_cash(self):
        self.payment()
        self.assertEqual(self.received(), dict(today=100.25, week=100.25, month=100.25))

    def test_today_positive_mpesa(self):
        self.payment(method="mpesa")
        self.assertEqual(self.received()["today"], 100.25)

    def test_other_actual_payment_methods(self):
        for method in ("bank_transfer", "card", "other"):
            self.payment(method=method)
        self.assertEqual(self.received()["today"], 300.75)

    def test_positive_adjustment_excluded(self):
        self.payment(method="adjustment")
        self.assertEqual(self.received(), dict(today=0, week=0, month=0))

    def test_negative_adjustment_excluded(self):
        self.payment(amount="-100.25", method="adjustment")
        self.assertEqual(self.received(), dict(today=0, week=0, month=0))

    def test_zero_and_negative_payment_excluded(self):
        self.payment(amount="0")
        self.payment(amount="-100.25")
        self.assertEqual(self.received(), dict(today=0, week=0, month=0))

    def test_previous_local_day_excluded_from_today(self):
        from datetime import timedelta
        self.payment(at=self.now - timedelta(hours=1))
        self.assertEqual(self.received(), dict(today=0, week=100.25, month=100.25))

    def test_current_week_monday_inclusive(self):
        self.payment(at=self.now.replace(day=12, hour=0, minute=0))
        self.assertEqual(self.received()["week"], 100.25)

    def test_before_current_week_excluded(self):
        from datetime import timedelta
        monday = self.now.replace(day=12, hour=0, minute=0)
        self.payment(at=monday - timedelta(microseconds=1))
        self.assertEqual(self.received(), dict(today=0, week=0, month=100.25))

    def test_current_month_start_inclusive(self):
        self.payment(at=self.now.replace(day=1, hour=0, minute=0))
        self.assertEqual(self.received()["month"], 100.25)

    def test_before_current_month_excluded(self):
        from datetime import timedelta
        start = self.now.replace(day=1, hour=0, minute=0)
        self.payment(at=start - timedelta(microseconds=1))
        self.assertEqual(self.received(), dict(today=0, week=0, month=0))

    def test_other_organization_excluded(self):
        self.payment(other=True)
        self.assertEqual(self.received(), dict(today=0, week=0, month=0))

    def test_today_start_inclusive_future_excluded(self):
        from datetime import timedelta
        self.payment(at=self.now.replace(hour=0, minute=0))
        self.payment(at=self.now + timedelta(microseconds=1))
        self.assertEqual(self.received(), dict(today=100.25, week=100.25, month=100.25))

    def test_week_crosses_month_boundary(self):
        from unittest.mock import patch
        now = self.now.replace(month=5, day=1, hour=12)
        self.payment(at=now.replace(month=4, day=30))
        with patch("reports.services.timezone.now", return_value=now):
            self.assertEqual(self.received(), dict(today=0, week=100.25, month=0))

    def test_empty_periods_and_single_aggregate_query(self):
        from reports.services import ReportService
        with self.assertNumQueries(1):
            self.assertEqual(ReportService._received_income(self.org), dict(today=0, week=0, month=0))

    def test_legacy_revenue_behavior_preserved(self):
        from unittest.mock import patch
        for amount, method in (("100", "cash"), ("50", "adjustment"), ("-20", "adjustment")):
            self.payment(amount=amount, method=method, at=self.now.replace(hour=12))
        MonthlyBill.objects.create(
            customer=self.customers[0], package_name="Test", package_price=Decimal("1000"),
            billing_month=10, billing_year=2026, invoice_date=date(2026, 10, 1),
            total_amount=Decimal("1000"), paid_amount=Decimal("400"), payment_status="partial",
        )
        with patch("reports.services.date") as legacy_date:
            legacy_date.today.return_value = date(2026, 10, 14)
            revenue = self.client.get("/api/reports/dashboard/").json()["revenue"]
        self.assertEqual(
            {key: revenue[key] for key in ("billed", "collected", "outstanding", "collection_rate", "today")},
            dict(billed=1000, collected=400, outstanding=600, collection_rate=40, today=130),
        )
        # Future entries contribute to the legacy whole-day sum but not the new totals.
        self.assertEqual(revenue["received"], dict(today=0, week=0, month=0))
