from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from mikrotik.models import MikrotikRouter
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class MikrotikRolePermissionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test ISP",
            slug="test-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.router = MikrotikRouter.objects.create(
            organization=self.organization,
            name="Main Router",
            host="10.0.0.1",
            port=8728,
            username="admin",
            password="test-password",
            is_active=True,
        )

        self.owner = self._create_user(
            username="owner",
            role="owner",
        )

        self.technician = self._create_user(
            username="technician",
            role="technician",
        )

        self.billing = self._create_user(
            username="billing",
            role="billing",
        )

        self.viewer = self._create_user(
            username="viewer",
            role="viewer",
        )

        self.client = APIClient()

    def _create_user(self, username, role):
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

    def _authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_viewer_can_list_routers(self):
        self._authenticate(self.viewer)

        response = self.client.get(
            "/api/mikrotik/routers/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_viewer_cannot_create_router(self):
        self._authenticate(self.viewer)

        response = self.client.post(
            "/api/mikrotik/routers/",
            {
                "name": "Blocked Router",
                "host": "10.0.0.2",
                "port": 8728,
                "username": "admin",
                "password": "password",
                "use_ssl": False,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            MikrotikRouter.objects.filter(
                organization=self.organization,
                name="Blocked Router",
            ).exists()
        )

    def test_viewer_cannot_delete_router(self):
        self._authenticate(self.viewer)

        response = self.client.delete(
            f"/api/mikrotik/routers/{self.router.id}/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            MikrotikRouter.objects.filter(
                id=self.router.id
            ).exists()
        )

    @patch("mikrotik.views.get_profiles")
    @patch("mikrotik.views.MikrotikConnection")
    def test_technician_can_use_network_action(
        self,
        mock_connection,
        mock_get_profiles,
    ):
        self._authenticate(self.technician)

        connection_instance = MagicMock()
        connection_instance.api = MagicMock()

        mock_connection.return_value = (
            connection_instance
        )

        mock_get_profiles.return_value = {
            "status": "Found",
            "profiles": [
                {
                    "name": "10Mbps",
                }
            ],
        }

        response = self.client.get(
            (
                f"/api/mikrotik/routers/"
                f"{self.router.id}/get_profiles/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["status"],
            "Success",
        )

        self.assertEqual(
            response.data["profiles"],
            ["10Mbps"],
        )

        mock_connection.assert_called_once()

    @patch("mikrotik.views.MikrotikConnection")
    def test_billing_user_cannot_use_network_action(
        self,
        mock_connection,
    ):
        self._authenticate(self.billing)

        response = self.client.get(
            (
                f"/api/mikrotik/routers/"
                f"{self.router.id}/get_profiles/"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_connection.assert_not_called()

    def test_owner_can_manage_router(self):
        self._authenticate(self.owner)

        update_response = self.client.patch(
            f"/api/mikrotik/routers/{self.router.id}/",
            {
                "description": "Updated by owner",
            },
            format="json",
        )

        self.assertEqual(
            update_response.status_code,
            200,
        )

        self.router.refresh_from_db()

        self.assertEqual(
            self.router.description,
            "Updated by owner",
        )

        delete_response = self.client.delete(
            f"/api/mikrotik/routers/{self.router.id}/"
        )

        self.assertEqual(
            delete_response.status_code,
            204,
        )

        self.assertFalse(
            MikrotikRouter.objects.filter(
                id=self.router.id
            ).exists()
        )