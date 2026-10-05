from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Package
from customers.models import (
    AddressZone,
    CustomerProfile,
    SupportTicket,
)
from mikrotik.models import RouterInfo
from organizations.models import Organization


class CustomerPortalTenantIsolationTests(TestCase):
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
            name="ISP A Package",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1000.00"),
            is_active=True,
        )

        self.package_b = Package.objects.create(
            organization=self.org_b,
            name="ISP B Package",
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
            address="Address A",
            zone=self.zone_a,
            package=self.package_a,
            customer_status="active",
        )

        self.customer_b = CustomerProfile.objects.create(
            organization=self.org_b,
            customer_id="B001",
            customer_name="Customer B",
            phone_number="0711000002",
            address="Address B",
            zone=self.zone_b,
            package=self.package_b,
            customer_status="active",
        )

        # Same PPPoE credentials under two different ISPs.
        # Organization slug must determine which customer logs in.
        self.router_info_a = RouterInfo.objects.create(
            customer=self.customer_a,
            pppoe_name="shareduser",
            pppoe_pass="sharedpass",
        )

        self.router_info_b = RouterInfo.objects.create(
            customer=self.customer_b,
            pppoe_name="shareduser",
            pppoe_pass="sharedpass",
        )

        # A second account exists only under ISP A.
        self.customer_a_only = CustomerProfile.objects.create(
            organization=self.org_a,
            customer_id="A002",
            customer_name="ISP A Only Customer",
            phone_number="0711000003",
            address="Address A2",
            zone=self.zone_a,
            package=self.package_a,
            customer_status="active",
        )

        self.router_info_a_only = RouterInfo.objects.create(
            customer=self.customer_a_only,
            pppoe_name="isp-a-only",
            pppoe_pass="onlypass",
        )

        self.ticket_a = SupportTicket.objects.create(
            customer=self.customer_a,
            title="Customer A Ticket",
            description="ISP A support issue",
            status="open",
        )

        self.ticket_b = SupportTicket.objects.create(
            customer=self.customer_b,
            title="Customer B Ticket",
            description="ISP B support issue",
            status="open",
        )

        self.client = APIClient()

    def test_public_packages_are_scoped_to_organization(self):
        response = self.client.get(
            "/api/portal/packages/",
            {"organization": "isp-a"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["name"],
            "ISP A Package",
        )

        package_names = [
            item["name"]
            for item in response.data
        ]

        self.assertNotIn(
            "ISP B Package",
            package_names,
        )

    def test_public_packages_without_organization_return_empty_list(self):
        response = self.client.get(
            "/api/portal/packages/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_same_pppoe_credentials_login_to_org_a(self):
        response = self.client.post(
            "/api/portal/auth/login/",
            {
                "organization": "isp-a",
                "pppoe_name": "shareduser",
                "pppoe_pass": "sharedpass",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["customer_id"],
            "A001",
        )
        self.assertEqual(
            response.data["organization"],
            "isp-a",
        )
        self.assertIn(
            "token",
            response.data,
        )

    def test_same_pppoe_credentials_login_to_org_b(self):
        response = self.client.post(
            "/api/portal/auth/login/",
            {
                "organization": "isp-b",
                "pppoe_name": "shareduser",
                "pppoe_pass": "sharedpass",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["customer_id"],
            "B001",
        )
        self.assertEqual(
            response.data["organization"],
            "isp-b",
        )

    def test_credentials_cannot_cross_organization_boundary(self):
        response = self.client.post(
            "/api/portal/auth/login/",
            {
                "organization": "isp-b",
                "pppoe_name": "isp-a-only",
                "pppoe_pass": "onlypass",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_customer_cannot_retrieve_another_customer_ticket(self):
        login_response = self.client.post(
            "/api/portal/auth/login/",
            {
                "organization": "isp-a",
                "pppoe_name": "shareduser",
                "pppoe_pass": "sharedpass",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        token = login_response.data["token"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        own_response = self.client.get(
            f"/api/portal/tickets/{self.ticket_a.id}/"
        )

        foreign_response = self.client.get(
            f"/api/portal/tickets/{self.ticket_b.id}/"
        )

        self.assertEqual(
            own_response.status_code,
            200,
        )

        self.assertEqual(
            foreign_response.status_code,
            404,
        )