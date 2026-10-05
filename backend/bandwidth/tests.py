from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from bandwidth.models import BandwidthSample
from bandwidth.services import (
    live_usage,
    record_snapshot,
    usage_logs,
)
from bandwidth.views import (
    LiveUsageView,
    SyncBandwidthView,
)
from mikrotik.models import MikrotikRouter
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class BandwidthTenantIsolationTests(TestCase):
    """
    Ensure bandwidth data and router access cannot cross
    organization boundaries.
    """

    def setUp(self):
        self.org_a = Organization.objects.create(
            name="ISP Alpha",
            slug="isp-alpha",
            organization_type="pppoe",
            status="active",
            is_active=True,
        )

        self.org_b = Organization.objects.create(
            name="ISP Beta",
            slug="isp-beta",
            organization_type="pppoe",
            status="active",
            is_active=True,
        )

        self.router_a = MikrotikRouter.objects.create(
            organization=self.org_a,
            name="Alpha Router",
            host="10.0.0.1",
            port=8728,
            username="admin",
            password="alpha-password",
            is_active=True,
        )

        self.router_b = MikrotikRouter.objects.create(
            organization=self.org_b,
            name="Beta Router",
            host="10.0.0.2",
            port=8728,
            username="admin",
            password="beta-password",
            is_active=True,
        )

        self.sample_a = BandwidthSample.objects.create(
            organization=self.org_a,
            router=self.router_a,
            pppoe_id="alpha-user",
            customer_name="Alpha Customer",
            upload_bytes=1000,
            download_bytes=5000,
            uptime="1h",
        )

        self.sample_b = BandwidthSample.objects.create(
            organization=self.org_b,
            router=self.router_b,
            pppoe_id="beta-user",
            customer_name="Beta Customer",
            upload_bytes=2000,
            download_bytes=8000,
            uptime="2h",
        )

    def test_usage_logs_only_return_current_organization(self):
        result = usage_logs(
            self.org_a,
            {},
        )

        ids = [
            row["id"]
            for row in result["results"]
        ]

        self.assertIn(
            self.sample_a.id,
            ids,
        )

        self.assertNotIn(
            self.sample_b.id,
            ids,
        )

        self.assertEqual(
            result["totals"]["upload_bytes"],
            1000,
        )

        self.assertEqual(
            result["totals"]["download_bytes"],
            5000,
        )

    def test_foreign_router_filter_cannot_expose_other_organization(self):
        result = usage_logs(
            self.org_a,
            {
                "router": self.router_b.id,
            },
        )

        self.assertEqual(
            result["results"],
            [],
        )

        self.assertEqual(
            result["totals"]["upload_bytes"],
            0,
        )

        self.assertEqual(
            result["totals"]["download_bytes"],
            0,
        )

        self.assertEqual(
            result["totals"]["total_bytes"],
            0,
        )

    @patch(
        "bandwidth.services.live._collect_router"
    )
    def test_live_usage_cannot_access_foreign_router(
        self,
        mock_collect_router,
    ):
        result = live_usage(
            self.org_a,
            self.router_b.id,
        )

        self.assertEqual(
            result["router_count"],
            0,
        )

        self.assertEqual(
            result["online_clients"],
            0,
        )

        self.assertFalse(
            result["router_connected"]
        )

        mock_collect_router.assert_not_called()

    @patch(
        "bandwidth.services.live._collect_router"
    )
    def test_live_usage_only_uses_organization_routers(
        self,
        mock_collect_router,
    ):
        mock_collect_router.return_value = (
            [],
            True,
        )

        result = live_usage(
            self.org_a
        )

        self.assertEqual(
            result["router_count"],
            1,
        )

        self.assertTrue(
            result["router_connected"]
        )

        mock_collect_router.assert_called_once()

        called_router = (
            mock_collect_router
            .call_args
            .args[0]
        )

        self.assertEqual(
            called_router.id,
            self.router_a.id,
        )

        self.assertEqual(
            called_router.organization_id,
            self.org_a.id,
        )

    @patch(
        "bandwidth.services.reports.live_usage"
    )
    def test_record_snapshot_stores_organization(
        self,
        mock_live_usage,
    ):
        mock_live_usage.return_value = {
            "router_connected": True,
            "router_count": 1,
            "online_clients": 1,
            "total_download_bytes": 9000,
            "total_upload_bytes": 3000,
            "timestamp": 0,
            "sessions": [
                {
                    "pppoe_id": "new-alpha-user",
                    "customer_id": None,
                    "customer_name": "New Alpha User",
                    "address": "192.168.1.20",
                    "caller_id": "AA:BB:CC:DD:EE:FF",
                    "uptime": "30m",
                    "download_bytes": 9000,
                    "upload_bytes": 3000,
                    "profile": "",
                    "billing_status": "unknown",
                    "balance": 0,
                    "router": self.router_a.name,
                    "router_id": self.router_a.id,
                }
            ],
        }

        result = record_snapshot(
            self.org_a,
            self.router_a.id,
        )

        self.assertEqual(
            result["recorded"],
            1,
        )

        sample = (
            BandwidthSample.objects
            .get(
                pppoe_id="new-alpha-user"
            )
        )

        self.assertEqual(
            sample.organization,
            self.org_a,
        )

        self.assertEqual(
            sample.router,
            self.router_a,
        )

        self.assertEqual(
            sample.upload_bytes,
            3000,
        )

        self.assertEqual(
            sample.download_bytes,
            9000,
        )


class BandwidthRolePermissionTests(TestCase):
    """
    Ensure bandwidth API permissions follow the
    organization role policy.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="Bandwidth Test ISP",
            slug="bandwidth-test-isp",
            organization_type="pppoe",
            status="active",
            is_active=True,
        )

        self.owner = self._create_user(
            "bandwidth_owner",
            "owner",
        )

        self.technician = self._create_user(
            "bandwidth_technician",
            "technician",
        )

        self.billing = self._create_user(
            "bandwidth_billing",
            "billing",
        )

        self.viewer = self._create_user(
            "bandwidth_viewer",
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

    @patch(
        "bandwidth.views.services.live_usage"
    )
    def test_viewer_can_view_live_usage(
        self,
        mock_live_usage,
    ):
        mock_live_usage.return_value = {
            "router_connected": True,
            "router_count": 0,
            "online_clients": 0,
            "sessions": [],
        }

        request = self._request(
            "get",
            "/bandwidth/live/",
            self.viewer,
        )

        response = LiveUsageView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_live_usage.assert_called_once_with(
            self.organization,
            None,
        )

    @patch(
        "bandwidth.views.services.live_usage"
    )
    def test_billing_user_can_view_live_usage(
        self,
        mock_live_usage,
    ):
        mock_live_usage.return_value = {
            "router_connected": True,
            "router_count": 0,
            "online_clients": 0,
            "sessions": [],
        }

        request = self._request(
            "get",
            "/bandwidth/live/",
            self.billing,
        )

        response = LiveUsageView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_live_usage.assert_called_once_with(
            self.organization,
            None,
        )

    @patch(
        "bandwidth.views.services.record_snapshot"
    )
    def test_technician_can_trigger_bandwidth_sync(
        self,
        mock_record_snapshot,
    ):
        mock_record_snapshot.return_value = {
            "recorded": 0,
            "status": "ok",
        }

        request = self._request(
            "post",
            "/bandwidth/sync/",
            self.technician,
            {},
        )

        response = SyncBandwidthView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_record_snapshot.assert_called_once_with(
            self.organization,
            None,
        )

    @patch(
        "bandwidth.views.services.record_snapshot"
    )
    def test_owner_can_trigger_bandwidth_sync(
        self,
        mock_record_snapshot,
    ):
        mock_record_snapshot.return_value = {
            "recorded": 0,
            "status": "ok",
        }

        request = self._request(
            "post",
            "/bandwidth/sync/",
            self.owner,
            {},
        )

        response = SyncBandwidthView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_record_snapshot.assert_called_once_with(
            self.organization,
            None,
        )

    @patch(
        "bandwidth.views.services.record_snapshot"
    )
    def test_billing_user_cannot_trigger_bandwidth_sync(
        self,
        mock_record_snapshot,
    ):
        request = self._request(
            "post",
            "/bandwidth/sync/",
            self.billing,
            {},
        )

        response = SyncBandwidthView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_record_snapshot.assert_not_called()

    @patch(
        "bandwidth.views.services.record_snapshot"
    )
    def test_viewer_cannot_trigger_bandwidth_sync(
        self,
        mock_record_snapshot,
    ):
        request = self._request(
            "post",
            "/bandwidth/sync/",
            self.viewer,
            {},
        )

        response = SyncBandwidthView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_record_snapshot.assert_not_called()