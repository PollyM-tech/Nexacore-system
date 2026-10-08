from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from auditlog.models import AuditLog
from olt.models import OltDevice
from olt.views import OltDeviceViewSet
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class OltRolePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="OLT Test ISP",
            slug="olt-test-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.olt = OltDevice.objects.create(
            organization=self.organization,
            name="Main OLT",
            host="10.20.30.40",
            telnet_port=23,
            web_port=80,
            protocol="http",
            olt_type="GENERIC_EPON",
            telnet_username="admin",
            telnet_password="test-password",
            snmp_port=161,
            snmp_community="public",
            timeout=10,
            is_active=True,
        )

        self.owner = self._create_user(
            "olt_owner",
            "owner",
        )

        self.technician = self._create_user(
            "olt_technician",
            "technician",
        )

        self.billing = self._create_user(
            "olt_billing",
            "billing",
        )

        self.viewer = self._create_user(
            "olt_viewer",
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

    def test_viewer_can_list_olts(self):
        view = OltDeviceViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/olts/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_viewer_cannot_create_olt(self):
        view = OltDeviceViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/olts/",
            self.viewer,
            {
                "name": "Blocked OLT",
                "host": "10.20.30.41",
                "telnet_port": 23,
                "web_port": 80,
                "protocol": "http",
                "olt_type": "GENERIC_EPON",
                "telnet_username": "admin",
                "telnet_password": "password",
                "snmp_port": 161,
                "snmp_community": "public",
                "timeout": 10,
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
            OltDevice.objects.filter(
                organization=self.organization,
                host="10.20.30.41",
            ).exists()
        )

    @patch("olt.views.OltSnmp")
    def test_technician_can_test_olt_connection(
        self,
        mock_snmp_class,
    ):
        mock_snmp = MagicMock()

        mock_snmp.system_info.return_value = {
            "description": "Test OLT",
            "uptime": "1 day",
        }

        mock_snmp_class.return_value = mock_snmp

        view = OltDeviceViewSet.as_view(
            {
                "post": "test_connection",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"test_connection/"
            ),
            self.technician,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["status"],
            "online",
        )

        mock_snmp_class.assert_called_once_with(
            self.olt.host,
            self.olt.snmp_community,
            self.olt.snmp_port,
            timeout=self.olt.timeout,
        )

        mock_snmp.system_info.assert_called_once()

        self.olt.refresh_from_db()

        self.assertEqual(
            self.olt.status,
            "online",
        )

        self.assertIsNotNone(
            self.olt.last_checked
        )

    @patch("olt.views.sync_onus")
    def test_technician_can_sync_onus(
        self,
        mock_sync_onus,
    ):
        mock_sync_onus.return_value = {
            "ok": True,
            "created": 2,
            "updated": 1,
        }

        view = OltDeviceViewSet.as_view(
            {
                "post": "sync_onus",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"sync_onus/"
            ),
            self.technician,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["ok"]
        )

        mock_sync_onus.assert_called_once()

        synced_olt = (
            mock_sync_onus
            .call_args
            .args[0]
        )

        self.assertEqual(
            synced_olt.pk,
            self.olt.pk,
        )

        self.olt.refresh_from_db()

        self.assertEqual(
            self.olt.status,
            "online",
        )

        self.assertIsNotNone(
            self.olt.last_checked
        )

    @patch("olt.views.OltSnmp")
    def test_billing_user_cannot_test_olt_connection(
        self,
        mock_snmp_class,
    ):
        view = OltDeviceViewSet.as_view(
            {
                "post": "test_connection",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"test_connection/"
            ),
            self.billing,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_snmp_class.assert_not_called()

    def test_owner_can_delete_olt(self):
        view = OltDeviceViewSet.as_view(
            {
                "delete": "destroy",
            }
        )

        request = self._request(
            "delete",
            f"/olts/{self.olt.pk}/",
            self.owner,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            OltDevice.objects.filter(
                pk=self.olt.pk
            ).exists()
        )


class OltAuditLogTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="OLT Audit ISP",
            slug="olt-audit-isp",
            organization_type="hybrid",
            status="active",
            country="KE",
            currency="KES",
            timezone="Africa/Nairobi",
            is_active=True,
        )

        self.olt = OltDevice.objects.create(
            organization=self.organization,
            name="Audit OLT",
            host="10.30.40.50",
            telnet_port=23,
            web_port=80,
            protocol="http",
            olt_type="GENERIC_EPON",
            telnet_username="admin",
            telnet_password="secret-password",
            snmp_port=161,
            snmp_community="private-community",
            timeout=10,
            is_active=True,
        )

        self.owner = self._create_user(
            "olt_audit_owner",
            "owner",
        )

        self.technician = self._create_user(
            "olt_audit_technician",
            "technician",
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

    def test_olt_creation_creates_audit_log(self):
        view = OltDeviceViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/olts/",
            self.technician,
            {
                "name": "Created Audit OLT",
                "host": "10.30.40.51",
                "telnet_port": 23,
                "web_port": 80,
                "protocol": "http",
                "olt_type": "GENERIC_EPON",
                "telnet_username": "admin",
                "telnet_password": "hidden-password",
                "snmp_port": 161,
                "snmp_community": "hidden-community",
                "timeout": 10,
                "description": "",
                "is_active": True,
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        olt = OltDevice.objects.get(
            organization=self.organization,
            name="Created Audit OLT",
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.device_created",
            resource_id=str(olt.pk),
        )

        self.assertEqual(
            log.user,
            self.technician,
        )

        self.assertNotIn(
            "telnet_password",
            log.metadata,
        )

        self.assertNotIn(
            "snmp_community",
            log.metadata,
        )

    def test_olt_update_creates_audit_log(self):
        view = OltDeviceViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self._request(
            "patch",
            f"/olts/{self.olt.pk}/",
            self.technician,
            {
                "description": "Updated audit OLT",
            },
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.device_updated",
            resource_id=str(self.olt.pk),
        )

        self.assertEqual(
            log.metadata["after"][
                "description"
            ],
            "Updated audit OLT",
        )

    def test_olt_delete_creates_audit_log(self):
        view = OltDeviceViewSet.as_view(
            {
                "delete": "destroy",
            }
        )

        olt_id = self.olt.pk

        request = self._request(
            "delete",
            f"/olts/{olt_id}/",
            self.owner,
        )

        response = view(
            request,
            pk=olt_id,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.device_deleted",
            resource_id=str(olt_id),
        )

        self.assertEqual(
            log.metadata["name"],
            "Audit OLT",
        )

    @patch("olt.views.OltSnmp")
    def test_successful_connection_test_creates_audit_log(
        self,
        mock_snmp_class,
    ):
        mock_snmp = MagicMock()
        mock_snmp.system_info.return_value = {
            "description": "Audit OLT",
        }

        mock_snmp_class.return_value = mock_snmp

        view = OltDeviceViewSet.as_view(
            {
                "post": "test_connection",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"test_connection/"
            ),
            self.technician,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.connection_test_succeeded",
            resource_id=str(self.olt.pk),
        )

        self.assertEqual(
            log.metadata["result"],
            "success",
        )

    @patch("olt.views.OltSnmp")
    def test_failed_connection_test_creates_audit_log(
        self,
        mock_snmp_class,
    ):
        mock_snmp = MagicMock()
        mock_snmp.system_info.return_value = None

        mock_snmp_class.return_value = mock_snmp

        view = OltDeviceViewSet.as_view(
            {
                "post": "test_connection",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"test_connection/"
            ),
            self.technician,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.connection_test_failed",
            resource_id=str(self.olt.pk),
        )

        self.assertEqual(
            log.metadata["result"],
            "failed",
        )

    @patch("olt.views.sync_onus")
    def test_onu_sync_creates_audit_log(
        self,
        mock_sync_onus,
    ):
        mock_sync_onus.return_value = {
            "ok": True,
            "created": 3,
            "updated": 2,
        }

        view = OltDeviceViewSet.as_view(
            {
                "post": "sync_onus",
            }
        )

        request = self._request(
            "post",
            (
                f"/olts/"
                f"{self.olt.pk}/"
                f"sync_onus/"
            ),
            self.technician,
        )

        response = view(
            request,
            pk=self.olt.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        log = AuditLog.objects.get(
            organization=self.organization,
            action="olt.onu_sync_succeeded",
            resource_id=str(self.olt.pk),
        )

        self.assertEqual(
            log.metadata["created"],
            3,
        )

        self.assertEqual(
            log.metadata["updated"],
            2,
        )