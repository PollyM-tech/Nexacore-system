"""Package usage and mutation guards at the API boundary."""
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from billing.models import Package
from customers.models import AddressZone, CustomerProfile
from mikrotik.models import RouterInfo
from organizations.models import Organization, OrganizationMembership


@override_settings(LINTECH_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class PackageSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Safety ISP", slug="safety")
        cls.other = Organization.objects.create(name="Other ISP", slug="other-safety")
        cls.user = get_user_model().objects.create_user(username="package-safety")
        OrganizationMembership.objects.create(organization=cls.org, user=cls.user, role="owner", is_active=True)
        cls.zone = AddressZone.objects.create(organization=cls.org, name="Zone")
        cls.package = Package.objects.create(organization=cls.org, name="Home", speed="5 Mbps", price="500")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/billing/packages/{self.package.pk}/"

    def customer(self, mode=None, organization=None):
        customer = CustomerProfile.objects.create(
            organization=organization or self.org, customer_id=str(CustomerProfile.objects.count()),
            customer_name="Subscriber", phone_number="0700000000", address="Address",
            zone=self.zone, package=self.package,
        )
        if mode:
            RouterInfo.objects.create(customer=customer, authentication_mode=mode,
                                      pppoe_name=f"subscriber-{customer.pk}", pppoe_pass="secret")
        return customer

    def test_list_and_detail_counts_include_only_configured_radius(self):
        self.customer()
        self.customer("local_secret")
        self.customer("radius")
        # Even malformed cross-tenant assignments must not leak into counts.
        self.customer("radius", self.other)
        for data in (self.client.get(self.url).data,
                     self.client.get("/api/billing/packages/").data["results"][0]):
            self.assertEqual(data["customer_count"], 3)
            self.assertEqual(data["radius_customer_count"], 1)
            self.assertNotIn("organization", data)

    def test_speed_change_without_radius(self):
        self.customer("local_secret")
        self.assertEqual(self.client.patch(self.url, {"speed": "10 Mbps"}).status_code, 200)
        self.package.refresh_from_db()
        self.assertEqual(self.package.speed, "10 Mbps")

    def test_speed_change_blocked_for_patch_and_put(self):
        self.customer("radius")
        for method in (self.client.patch, self.client.put):
            response = method(self.url, {"name": "Home", "speed": "10 Mbps", "price": "700"})
            self.assertEqual(response.status_code, 400)
            self.assertIn("speed", response.data)
        self.package.refresh_from_db()
        self.assertEqual(self.package.speed, "5 Mbps")
        self.assertEqual(self.package.price, 500)

    def test_unrelated_and_same_speed_edits_allowed(self):
        self.customer("radius")
        for fields in ({"price": "700"}, {"description": "Updated"}, {"speed": "5 Mbps"},
                       {"name": "Renamed", "package_type": "quarterly"}):
            response = self.client.patch(self.url, fields)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["radius_customer_count"], 1)

    def test_deactivation_preserves_assignment_and_credentials(self):
        customer = self.customer("radius")
        response = self.client.patch(self.url + "toggle_status/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])
        customer.refresh_from_db()
        self.assertEqual(customer.package_id, self.package.pk)
        self.assertEqual(customer.router_info.pppoe_pass, "secret")
        self.assertEqual(response.data["customer_count"], 1)

    def test_delete_empty_package(self):
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(Package.objects.filter(pk=self.package.pk).exists())

    def test_delete_assigned_package_rejected_without_clearing_assignment(self):
        customer = self.customer()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Deactivate", str(response.data))
        customer.refresh_from_db()
        self.assertEqual(customer.package_id, self.package.pk)

    def test_other_tenant_does_not_block_or_affect_counts(self):
        self.customer("radius", self.other)
        response = self.client.patch(self.url, {"speed": "10 Mbps"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer_count"], 0)
        self.assertEqual(response.data["radius_customer_count"], 0)

    def test_other_tenant_package_inaccessible(self):
        package = Package.objects.create(organization=self.other, name="Private", speed="5 Mbps", price=500)
        url = f"/api/billing/packages/{package.pk}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"speed": "10 Mbps"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_list_query_count_does_not_grow_per_package(self):
        self.customer("radius")
        with CaptureQueriesContext(connection) as first:
            self.assertEqual(self.client.get("/api/billing/packages/").status_code, 200)
        for i in range(4):
            Package.objects.create(organization=self.org, name=f"Extra {i}", speed="5 Mbps", price=500)
        with CaptureQueriesContext(connection) as second:
            self.assertEqual(self.client.get("/api/billing/packages/").status_code, 200)
        self.assertEqual(len(first), len(second))

    def test_create_response_has_zero_read_only_counts(self):
        response = self.client.post("/api/billing/packages/", {
            "name": "New", "speed": "10 Mbps", "price": "1000",
            "customer_count": 99, "radius_customer_count": 99,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["customer_count"], 0)
        self.assertEqual(response.data["radius_customer_count"], 0)
