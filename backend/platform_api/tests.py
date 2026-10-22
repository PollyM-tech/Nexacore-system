from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from auditlog.models import AuditLog
from billing.models import Package
from customers.models import AddressZone, CustomerProfile
from mikrotik.models import MikrotikRouter
from organizations.models import Organization, OrganizationMembership
from .redaction import redact_metadata


class PlatformTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.root = User.objects.create_superuser(username="platform", email="root@example.test", password="test-only-password")
        cls.owner = User.objects.create_user(username="owner", password="test-only-password")
        cls.staff = User.objects.create_user(username="staff", is_staff=True)
        cls.other_user = User.objects.create_user(username="other")
        cls.org = Organization.objects.create(name="ISP One", slug="isp-one")
        cls.other = Organization.objects.create(name="ISP Two", slug="isp-two", status="suspended", is_active=False)
        cls.membership = OrganizationMembership.objects.create(organization=cls.org, user=cls.owner, role="owner")
        cls.other_membership = OrganizationMembership.objects.create(organization=cls.other, user=cls.other_user, role="owner")
        for org in [cls.org, cls.other]:
            zone = AddressZone.objects.create(organization=org, name="Zone")
            Package.objects.create(organization=org, name="Home", speed="5 Mbps", price=500)
            CustomerProfile.objects.create(organization=org, zone=zone, customer_id="C1", customer_name="Subscriber", phone_number="0700000000", address="Address")
            # No router password needed for inventory-only count tests.
            MikrotikRouter.objects.create(organization=org, name="Router", host="10.0.0.1", username="api")
        for org in [cls.org, cls.other, None]:
            AuditLog.objects.create(organization=org, user=cls.root, action="test.event", metadata={
                "consumer_secret": "hidden", "nested": [{"api-key": "hidden", "safe": "visible", "accessToken": "hidden"}],
                "record": {"attribute": "Cleartext-Password", "value": "hidden"},
            })

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.root)
        self.org_url = f"/api/platform/organizations/{self.org.pk}/"
        self.members_url = self.org_url + "members/"
        self.member_url = self.members_url + f"{self.membership.pk}/"

    def test_me_no_membership_required_and_safe_identity(self):
        self.assertFalse(self.root.organization_memberships.exists())
        response = self.client.get("/api/platform/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_platform_admin"], True)
        self.assertEqual(set(response.data["user"]), {"id", "email", "username", "first_name", "last_name"})

    def test_all_platform_endpoints_reject_normal_staff_owner_and_anonymous(self):
        urls = ["/api/platform/me/", "/api/platform/summary/", "/api/platform/organizations/", self.org_url,
                self.members_url, self.member_url, "/api/platform/users/", "/api/platform/audit/"]
        for user in [self.owner, self.staff, None]:
            self.client.force_authenticate(user)
            for url in urls:
                with self.subTest(user=str(user), url=url):
                    self.assertIn(self.client.get(url).status_code, [403] if user else [401, 403])
            self.assertIn(self.client.post("/api/platform/organizations/", {"name": "Bad", "slug": "bad"}).status_code, [401, 403])
            self.assertIn(self.client.patch(self.org_url, {"name": "Bad"}).status_code, [401, 403])
            self.assertIn(self.client.delete(self.member_url).status_code, [401, 403])

    def test_all_organizations_and_counts(self):
        response = self.client.get("/api/platform/organizations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        for row in response.data["results"]:
            for field in ["member_count", "customer_count", "router_count", "package_count"]:
                self.assertEqual(row[field], 1)
            self.assertNotIn("password", row)
        self.assertEqual(self.client.get(self.org_url).data["customer_count"], 1)

    def test_count_queries_do_not_grow_with_organizations(self):
        with CaptureQueriesContext(connection) as first:
            self.client.get("/api/platform/organizations/")
        for i in range(3):
            Organization.objects.create(name=f"Extra {i}", slug=f"extra-{i}")
        with CaptureQueriesContext(connection) as second:
            self.client.get("/api/platform/organizations/")
        self.assertEqual(len(first), len(second))

    def test_create_update_and_no_organization_delete(self):
        response = self.client.post("/api/platform/organizations/", {"name": "New ISP", "slug": "new-isp"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["customer_count"], 0)
        response = self.client.patch(self.org_url, {"name": "Updated", "status": "suspended"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])
        self.assertEqual(self.client.delete(self.org_url).status_code, 405)
        response = self.client.patch(self.org_url, {"is_active": True})
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(self.client.patch(self.org_url, {"status": "suspended", "is_active": True}).status_code, 400)
        self.assertEqual(self.client.post("/api/platform/organizations/", {"name": "Dup", "slug": "new-isp"}).status_code, 400)

    def test_members_list_add_duplicate_and_roles(self):
        self.assertEqual(self.client.get(self.members_url).data["count"], 1)
        response = self.client.post(self.members_url, {"user_id": self.staff.pk, "role": "technician"})
        self.assertEqual(response.status_code, 201, response.data)
        url = self.members_url + f"{response.data['id']}/"
        self.assertNotIn("password", str(response.data))
        self.assertEqual(self.client.post(self.members_url, {"user_id": self.staff.pk}).status_code, 400)
        self.assertEqual(self.client.patch(url, {"role": "admin"}).status_code, 200)
        self.assertEqual(self.client.patch(url, {"role": "superadmin"}).status_code, 400)
        self.assertEqual(self.client.patch(url, {"is_active": False}).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_cross_organization_membership_mismatch(self):
        url = self.members_url + f"{self.other_membership.pk}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"role": "admin"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_last_owner_protection(self):
        for body in [{"role": "admin"}, {"is_active": False}]:
            self.assertEqual(self.client.patch(self.member_url, body).status_code, 400)
        self.assertEqual(self.client.delete(self.member_url).status_code, 400)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, "owner")
        self.assertTrue(self.membership.is_active)
        OrganizationMembership.objects.create(organization=self.org, user=self.staff, role="owner")
        self.assertEqual(self.client.delete(self.member_url).status_code, 204)

    def test_inactive_user_does_not_count_as_replacement_owner(self):
        self.staff.is_active = False
        self.staff.save()
        OrganizationMembership.objects.create(organization=self.org, user=self.staff, role="owner")
        self.assertEqual(self.client.delete(self.member_url).status_code, 400)

    def test_user_identity_cannot_be_reassigned(self):
        response = self.client.patch(self.member_url, {"user_id": self.staff.pk})
        self.assertEqual(response.status_code, 400)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.user_id, self.owner.pk)

    def test_summary_cross_tenant_counts(self):
        response = self.client.get("/api/platform/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["organizations"], {"total": 2, "active": 1})
        self.assertEqual(response.data["users"], {"total": 4})
        for field in ["customers", "routers", "packages"]:
            self.assertEqual(response.data[field], {"total": 2, "active": 2})

    def test_audit_cross_tenant_filters_pagination_and_redaction(self):
        response = self.client.get("/api/platform/audit/", {"page_size": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])
        self.assertNotIn("hidden", str(response.data))
        self.assertIn("visible", str(response.data))
        response = self.client.get("/api/platform/audit/", {"organization": self.org.pk, "user": self.root.pk, "action": "test.event"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["actor"]["id"], self.root.pk)
        self.assertEqual(self.client.post("/api/platform/audit/", {}).status_code, 405)

    def test_redaction_nested_keys_and_no_input_mutation(self):
        original = {"PasswordHash": "hidden", "nested": [{"RADIUS_shared_secret": "hidden", "pppoe_pass": "hidden", "api_key": "hidden", "ConsumerKey": "hidden", "passkey": "hidden", "pwd": "hidden", "safe": 4}]}
        clean = redact_metadata(original)
        self.assertNotIn("hidden", str(clean))
        self.assertEqual(original["PasswordHash"], "hidden")
        self.assertEqual(clean["nested"][0]["safe"], 4)

    def test_users_paginated_safe_fields_and_counts(self):
        response = self.client.get("/api/platform/users/", {"page_size": 2})
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 2)
        for row in response.data["results"]:
            self.assertNotIn("password", row)
            self.assertNotIn("token", row)
            self.assertIn("membership_count", row)
        self.assertEqual(self.client.post("/api/platform/users/", {}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/platform/users/{self.owner.pk}/").status_code, 405)

    def test_mutations_audited_without_credentials(self):
        self.client.patch(self.org_url, {"name": "Renamed"})
        event = AuditLog.objects.get(action="platform.organization_updated")
        self.assertEqual(event.actor_role, "platform_admin")
        self.assertEqual(event.user_id, self.root.pk)
        self.assertEqual(event.organization_id, self.org.pk)
        self.assertEqual(event.metadata, {"changed_fields": ["name"]})

    def test_multiple_related_rows_do_not_multiply_usage_counts(self):
        OrganizationMembership.objects.create(organization=self.org, user=self.staff, role="viewer")
        zone = AddressZone.objects.get(organization=self.org)
        CustomerProfile.objects.create(organization=self.org, zone=zone, customer_id="C2", customer_name="Second", phone_number="0700000001", address="Address")
        CustomerProfile.objects.create(organization=self.org, zone=zone, customer_id="C3", customer_name="Third", phone_number="0700000002", address="Address")
        row = self.client.get(self.org_url).data
        self.assertEqual([row[k] for k in ["member_count", "customer_count", "router_count", "package_count"]], [2, 3, 1, 1])

    def test_summary_active_means_configuration_or_account_state(self):
        CustomerProfile.objects.filter(organization=self.other).update(customer_status="disconnected")
        MikrotikRouter.objects.filter(organization=self.other).update(is_active=False)
        Package.objects.filter(organization=self.other).update(is_active=False)
        data = self.client.get("/api/platform/summary/").data
        for field in ["customers", "routers", "packages"]:
            self.assertEqual(data[field], {"total": 2, "active": 1})

    def test_superuser_flag_does_not_require_staff_flag(self):
        self.root.is_staff = False
        self.root.save()
        self.assertEqual(self.client.get("/api/platform/me/").status_code, 200)

    def test_audit_is_newest_first_and_second_page_complete(self):
        first = self.client.get("/api/platform/audit/", {"page_size": 2}).data
        second = self.client.get("/api/platform/audit/", {"page_size": 2, "page": 2}).data
        ids = [row["id"] for row in first["results"] + second["results"]]
        self.assertEqual(ids, list(AuditLog.objects.order_by("-created_at", "-pk").values_list("pk", flat=True)))

    def test_no_unguarded_router_discovery_endpoint(self):
        for user in [self.root, self.owner, None]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/platform/").status_code, 404)
