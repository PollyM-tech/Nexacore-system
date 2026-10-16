from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from billing.models import Package
from customers.models import (
    AddressZone,
    CustomerProfile,
)
from organizations.models import (
    Organization,
    OrganizationMembership,
)
from radius.services import (
    RadiusAccountingService,
    RadiusProvisioningError,
)


User = get_user_model()


class RadiusSessionApiTests(APITestCase):
    def setUp(self):
        self.organization = (
            self._create_organization(
                name="Alpha ISP",
                slug="alpha-isp",
            )
        )

        self.other_organization = (
            self._create_organization(
                name="Beta ISP",
                slug="beta-isp",
            )
        )

        self.user = self._create_user(
            username="alpha-owner",
            organization=self.organization,
            role="owner",
        )

        self.other_user = (
            self._create_user(
                username="beta-owner",
                organization=(
                    self.other_organization
                ),
                role="owner",
            )
        )

        self.zone = (
            AddressZone.objects.create(
                organization=self.organization,
                name="Alpha Zone",
            )
        )

        self.other_zone = (
            AddressZone.objects.create(
                organization=(
                    self.other_organization
                ),
                name="Beta Zone",
            )
        )

        self.package = (
            Package.objects.create(
                organization=self.organization,
                name="Alpha 10 Mbps",
                package_type="monthly",
                speed="10 Mbps",
                price=Decimal("1500.00"),
                is_active=True,
            )
        )

        self.other_package = (
            Package.objects.create(
                organization=(
                    self.other_organization
                ),
                name="Beta 20 Mbps",
                package_type="monthly",
                speed="20 Mbps",
                price=Decimal("2500.00"),
                is_active=True,
            )
        )

        self.customer = (
            CustomerProfile.objects.create(
                organization=self.organization,
                customer_id="TEST001",
                customer_name=(
                    "Alpha Customer"
                ),
                phone_number="0711000001",
                address="Alpha Address",
                zone=self.zone,
                package=self.package,
                customer_status="active",
                balance=Decimal("0.00"),
            )
        )

        self.other_customer = (
            CustomerProfile.objects.create(
                organization=(
                    self.other_organization
                ),
                customer_id="TEST001",
                customer_name=(
                    "Beta Customer"
                ),
                phone_number="0722000002",
                address="Beta Address",
                zone=self.other_zone,
                package=self.other_package,
                customer_status="active",
                balance=Decimal("0.00"),
            )
        )

        self.session = {
            "id": 101,
            "username": (
                "alpha-isp-test001"
            ),
            "customer_id": "TEST001",
            "customer_name": (
                "Alpha Customer"
            ),
            "router_id": 1,
            "router_name": (
                "Alpha Router"
            ),
            "nas_ip_address": (
                "192.0.2.1"
            ),
            "ip_address": (
                "10.10.0.10"
            ),
            "mac_address": (
                "AA:BB:CC:DD:EE:01"
            ),
            "started_at": None,
            "updated_at": None,
            "stopped_at": None,
            "duration_seconds": 120,
            "download_bytes": 1000,
            "upload_bytes": 500,
            "total_bytes": 1500,
            "online": True,
            "terminate_cause": None,
            "service_type": (
                "Framed-User"
            ),
        }

        self.stopped_session = {
            **self.session,
            "id": 102,
            "online": False,
            "duration_seconds": 300,
            "stopped_at": None,
            "total_bytes": 4000,
        }

        self.client.force_authenticate(
            user=self.user
        )

    @staticmethod
    def _create_organization(
        name,
        slug,
    ):
        return (
            Organization.objects.create(
                name=name,
                slug=slug,
                organization_type=(
                    "hybrid"
                ),
                status="active",
                country="KE",
                currency="KES",
                timezone=(
                    "Africa/Nairobi"
                ),
                is_active=True,
            )
        )

    @staticmethod
    def _create_user(
        username,
        organization,
        role,
    ):
        user = (
            User.objects.create_user(
                username=username,
                password=(
                    "testpass123"
                ),
            )
        )

        (
            OrganizationMembership
            .objects
            .create(
                organization=organization,
                user=user,
                role=role,
                is_active=True,
            )
        )

        return user

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "organization_session_data"
    )
    def test_session_list_returns_sessions(
        self,
        mock_session_data,
    ):
        mock_session_data.return_value = [
            self.session,
            self.stopped_session,
        ]

        response = self.client.get(
            reverse(
                "radius-session-list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        self.assertEqual(
            response.data[
                "results"
            ][0]["customer_id"],
            "TEST001",
        )

        (
            mock_session_data
            .assert_called_once_with(
                self.organization,
                active_only=False,
            )
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "organization_session_data"
    )
    def test_active_sessions_returns_only_active_data(
        self,
        mock_session_data,
    ):
        mock_session_data.return_value = [
            self.session,
        ]

        response = self.client.get(
            reverse(
                "radius-active-sessions"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertTrue(
            response.data[
                "results"
            ][0]["online"]
        )

        (
            mock_session_data
            .assert_called_once_with(
                self.organization,
                active_only=True,
            )
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "customer_session_data"
    )
    def test_customer_sessions_returns_history(
        self,
        mock_customer_data,
    ):
        mock_customer_data.return_value = [
            self.session,
            self.stopped_session,
        ]

        response = self.client.get(
            reverse(
                "radius-customer-sessions",
                kwargs={
                    "customer_id": (
                        "TEST001"
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "customer_id"
            ],
            "TEST001",
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        (
            mock_customer_data
            .assert_called_once_with(
                self.organization,
                "TEST001",
            )
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "customer_session_data"
    )
    def test_unknown_customer_sessions_returns_404(
        self,
        mock_customer_data,
    ):
        mock_customer_data.side_effect = (
            RadiusProvisioningError(
                "Customer not found."
            )
        )

        response = self.client.get(
            reverse(
                "radius-customer-sessions",
                kwargs={
                    "customer_id": (
                        "UNKNOWN"
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["status"],
            "error",
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "latest_customer_session"
    )
    @patch(
        "radius.views."
        "RadiusAccountingService."
        "customer_is_online"
    )
    @patch(
        "radius.views."
        "RadiusAccountingService."
        "customer_totals"
    )
    @patch(
        "radius.views."
        "RadiusAccountingService."
        "_get_customer"
    )
    @patch(
        "radius.views."
        "RadiusAccountingService."
        "session_to_dict"
    )
    def test_customer_summary_returns_totals(
        self,
        mock_session_to_dict,
        mock_get_customer,
        mock_totals,
        mock_online,
        mock_latest,
    ):
        mock_get_customer.return_value = (
            self.customer
        )

        mock_totals.return_value = {
            "session_count": 2,
            "total_session_seconds": 420,
            "total_input_bytes": 2000,
            "total_output_bytes": 1000,
        }

        mock_online.return_value = True
        mock_latest.return_value = object()

        mock_session_to_dict.return_value = (
            self.session
        )

        response = self.client.get(
            reverse(
                "radius-customer-summary",
                kwargs={
                    "customer_id": (
                        "TEST001"
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "customer_id"
            ],
            "TEST001",
        )

        self.assertEqual(
            response.data[
                "customer_name"
            ],
            "Alpha Customer",
        )

        self.assertTrue(
            response.data[
                "online"
            ]
        )

        self.assertEqual(
            response.data[
                "totals"
            ][
                "session_count"
            ],
            2,
        )

        (
            mock_get_customer
            .assert_called_once_with(
                self.organization,
                "TEST001",
            )
        )

        mock_totals.assert_called_once_with(
            self.organization,
            "TEST001",
        )

        mock_online.assert_called_once_with(
            self.organization,
            "TEST001",
        )

        mock_latest.assert_called_once_with(
            self.organization,
            "TEST001",
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "_get_customer"
    )
    def test_unknown_customer_summary_returns_404(
        self,
        mock_get_customer,
    ):
        mock_get_customer.side_effect = (
            RadiusProvisioningError(
                "Customer not found."
            )
        )

        response = self.client.get(
            reverse(
                "radius-customer-summary",
                kwargs={
                    "customer_id": (
                        "UNKNOWN"
                    ),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["status"],
            "error",
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "organization_session_data"
    )
    def test_result_limit_is_applied(
        self,
        mock_session_data,
    ):
        mock_session_data.return_value = [
            {
                **self.session,
                "id": number,
            }
            for number
            in range(1, 11)
        ]

        response = self.client.get(
            reverse(
                "radius-session-list"
            ),
            {
                "limit": 3,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            3,
        )

        self.assertEqual(
            len(
                response.data[
                    "results"
                ]
            ),
            3,
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "organization_session_data"
    )
    def test_session_list_is_scoped_to_user_organization(
        self,
        mock_session_data,
    ):
        def organization_sessions(
            organization,
            active_only=False,
        ):
            if (
                organization
                == self.organization
            ):
                return [
                    {
                        **self.session,
                        "customer_name": (
                            "Alpha Customer"
                        ),
                    }
                ]

            if (
                organization
                == self.other_organization
            ):
                return [
                    {
                        **self.session,
                        "username": (
                            "beta-isp-test001"
                        ),
                        "customer_name": (
                            "Beta Customer"
                        ),
                    }
                ]

            return []

        mock_session_data.side_effect = (
            organization_sessions
        )

        alpha_response = (
            self.client.get(
                reverse(
                    "radius-session-list"
                )
            )
        )

        self.assertEqual(
            alpha_response.status_code,
            200,
        )

        self.assertEqual(
            alpha_response.data[
                "results"
            ][0][
                "customer_name"
            ],
            "Alpha Customer",
        )

        self.client.force_authenticate(
            user=self.other_user
        )

        beta_response = (
            self.client.get(
                reverse(
                    "radius-session-list"
                )
            )
        )

        self.assertEqual(
            beta_response.status_code,
            200,
        )

        self.assertEqual(
            beta_response.data[
                "results"
            ][0][
                "customer_name"
            ],
            "Beta Customer",
        )

    @patch(
        "radius.views."
        "RadiusAccountingService."
        "customer_session_data"
    )
    def test_same_customer_id_is_tenant_scoped(
        self,
        mock_customer_data,
    ):
        def customer_sessions(
            organization,
            customer_id,
        ):
            if (
                organization
                == self.organization
            ):
                return [
                    {
                        **self.session,
                        "customer_name": (
                            "Alpha Customer"
                        ),
                    }
                ]

            if (
                organization
                == self.other_organization
            ):
                return [
                    {
                        **self.session,
                        "username": (
                            "beta-isp-test001"
                        ),
                        "customer_name": (
                            "Beta Customer"
                        ),
                    }
                ]

            return []

        mock_customer_data.side_effect = (
            customer_sessions
        )

        url = reverse(
            "radius-customer-sessions",
            kwargs={
                "customer_id": (
                    "TEST001"
                ),
            },
        )

        alpha_response = (
            self.client.get(
                url
            )
        )

        self.assertEqual(
            alpha_response.data[
                "results"
            ][0][
                "customer_name"
            ],
            "Alpha Customer",
        )

        self.client.force_authenticate(
            user=self.other_user
        )

        beta_response = (
            self.client.get(
                url
            )
        )

        self.assertEqual(
            beta_response.data[
                "results"
            ][0][
                "customer_name"
            ],
            "Beta Customer",
        )

    def test_unauthenticated_request_is_denied(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "radius-session-list"
            )
        )

        self.assertIn(
            response.status_code,
            (
                401,
                403,
            ),
        )


class RadiusAccountingMappingTests(
    APITestCase
):
    def test_session_byte_direction_matches_customer_perspective(
        self,
    ):
        session = SimpleNamespace(
            radacctid=1,
            username="test-user",
            nasipaddress=(
                "192.168.88.1"
            ),
            framedipaddress=(
                "10.0.0.10"
            ),
            callingstationid=(
                "AA:BB:CC:DD:EE:FF"
            ),
            acctstarttime=None,
            acctupdatetime=None,
            acctstoptime=None,
            acctsessiontime=60,
            acctinputoctets=1_000,
            acctoutputoctets=5_000,
            total_bytes=6_000,
            is_active=True,
            acctterminatecause=None,
            servicetype="Framed-User",
        )

        result = (
            RadiusAccountingService
            .session_to_dict(
                session,
                customer=None,
            )
        )

        self.assertEqual(
            result[
                "upload_bytes"
            ],
            1_000,
        )

        self.assertEqual(
            result[
                "download_bytes"
            ],
            5_000,
        )

        self.assertEqual(
            result[
                "total_bytes"
            ],
            6_000,
        )

    def test_fresh_session_is_online(
        self,
    ):
        now = timezone.now()

        session = SimpleNamespace(
            acctstarttime=(
                now
                - timedelta(
                    minutes=20
                )
            ),
            acctupdatetime=(
                now
                - timedelta(
                    minutes=4
                )
            ),
            acctstoptime=None,
        )

        self.assertTrue(
            RadiusAccountingService
            .is_session_online(
                session,
                now=now,
            )
        )

    def test_stale_session_is_offline(
        self,
    ):
        now = timezone.now()

        session = SimpleNamespace(
            acctstarttime=(
                now
                - timedelta(
                    hours=2
                )
            ),
            acctupdatetime=(
                now
                - timedelta(
                    minutes=16
                )
            ),
            acctstoptime=None,
        )

        self.assertFalse(
            RadiusAccountingService
            .is_session_online(
                session,
                now=now,
            )
        )

    def test_stopped_session_is_offline(
        self,
    ):
        now = timezone.now()

        session = SimpleNamespace(
            acctstarttime=(
                now
                - timedelta(
                    minutes=10
                )
            ),
            acctupdatetime=(
                now
                - timedelta(
                    minutes=1
                )
            ),
            acctstoptime=now,
        )

        self.assertFalse(
            RadiusAccountingService
            .is_session_online(
                session,
                now=now,
            )
        )

    def test_new_session_without_interim_update_is_online(
        self,
    ):
        now = timezone.now()

        session = SimpleNamespace(
            acctstarttime=(
                now
                - timedelta(
                    minutes=3
                )
            ),
            acctupdatetime=None,
            acctstoptime=None,
        )

        self.assertTrue(
            RadiusAccountingService
            .is_session_online(
                session,
                now=now,
            )
        )

    def test_old_session_without_interim_update_is_stale(
        self,
    ):
        now = timezone.now()

        session = SimpleNamespace(
            acctstarttime=(
                now
                - timedelta(
                    minutes=20
                )
            ),
            acctupdatetime=None,
            acctstoptime=None,
        )

        self.assertFalse(
            RadiusAccountingService
            .is_session_online(
                session,
                now=now,
            )
        )