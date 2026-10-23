from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from organizations.models import Organization, OrganizationMembership


class StaffIdentityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operator", email="operator@example.test")
        self.org = Organization.objects.create(name="ISP", slug="identity-isp")
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=self.org, role="owner")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_verified_owner_and_safe_identity(self):
        response = self.client.get("/api/auth/user/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_platform_admin"])
        self.assertEqual(response.data["membership"], {"role": "owner", "role_label": "Owner", "organization": {"id": self.org.pk, "name": "ISP", "slug": "identity-isp"}})
        self.assertNotIn("password", response.data)

    def test_superadmin_is_separate_from_membership_role(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get("/api/auth/user/")
        self.assertTrue(response.data["is_platform_admin"])
        self.assertEqual(response.data["membership"]["role"], "owner")

    def test_inactive_membership_or_organization_is_not_displayed(self):
        self.membership.is_active = False
        self.membership.save()
        self.assertIsNone(self.client.get("/api/auth/user/").data["membership"])
        self.membership.is_active = True
        self.membership.save()
        self.org.is_active = False
        self.org.save()
        self.assertIsNone(self.client.get("/api/auth/user/").data["membership"])

    def test_another_users_membership_is_not_exposed(self):
        user = get_user_model().objects.create_user(username="unassigned")
        self.client.force_authenticate(user)
        self.assertIsNone(self.client.get("/api/auth/user/").data["membership"])

    def test_privilege_fields_are_read_only(self):
        response = self.client.patch("/api/auth/user/", {"is_platform_admin": True, "membership": {"role": "admin"}}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.membership.role, "owner")

    def test_anonymous_cannot_read_identity(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get("/api/auth/user/").status_code, (401, 403))
