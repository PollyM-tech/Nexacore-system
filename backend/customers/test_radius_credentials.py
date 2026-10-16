from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import serializers

from customers.service import CustomerService


class RadiusCredentialConsistencyTests(
    TestCase
):
    def _build_customer(
        self,
        password="old-password",
    ):
        organization = SimpleNamespace(
            id=1,
        )

        package = SimpleNamespace(
            name="HomePlan",
        )

        router = SimpleNamespace(
            id=2,
        )

        info = SimpleNamespace(
            authentication_mode="radius",
            pppoe_name="lintech-demo-test001",
            pppoe_pass=password,
            profile_name="HomePlan",
            remote_ip=None,
            router=router,
            save=MagicMock(),
        )

        customer = SimpleNamespace(
            id=1,
            pk=1,
            customer_id="TEST001",
            organization=organization,
            package=package,
            router_info=info,
        )

        return (
            organization,
            customer,
            info,
        )

    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "provision_pppoe_customer"
    )
    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "build_radius_username"
    )
    @patch(
        "customers.service."
        "CustomerProfile.objects.filter"
    )
    def test_radius_password_change_updates_radius_and_router_info(
        self,
        mock_filter,
        mock_build_username,
        mock_provision,
    ):
        (
            organization,
            customer,
            info,
        ) = self._build_customer()

        queryset = MagicMock()

        mock_filter.return_value = queryset

        (
            queryset
            .select_related
            .return_value
            .first
            .return_value
        ) = customer

        mock_build_username.return_value = (
            "lintech-demo-test001"
        )

        mock_provision.return_value = {
            "username": (
                "lintech-demo-test001"
            ),
            "password": (
                "new-radius-password"
            ),
            "rate_limit": "5M/5M",
            "created": False,
        }

        result_customer, warning = (
            CustomerService
            .update_customer_connection(
                organization,
                "TEST001",
                {
                    "pppoe_pass": (
                        "new-radius-password"
                    ),
                },
            )
        )

        self.assertIs(
            result_customer,
            customer,
        )

        self.assertIsNone(
            warning
        )

        mock_provision.assert_called_once_with(
            customer,
            password="new-radius-password",
            reset_password=True,
        )

        self.assertEqual(
            info.pppoe_name,
            "lintech-demo-test001",
        )

        self.assertEqual(
            info.pppoe_pass,
            "new-radius-password",
        )

        info.save.assert_called_once()

    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "provision_pppoe_customer"
    )
    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "build_radius_username"
    )
    @patch(
        "customers.service."
        "CustomerProfile.objects.filter"
    )
    def test_radius_update_without_password_keeps_existing_radius_password(
        self,
        mock_filter,
        mock_build_username,
        mock_provision,
    ):
        (
            organization,
            customer,
            info,
        ) = self._build_customer(
            password="existing-password"
        )

        queryset = MagicMock()

        mock_filter.return_value = queryset

        (
            queryset
            .select_related
            .return_value
            .first
            .return_value
        ) = customer

        mock_build_username.return_value = (
            "lintech-demo-test001"
        )

        mock_provision.return_value = {
            "username": (
                "lintech-demo-test001"
            ),
            "password": (
                "existing-password"
            ),
            "rate_limit": "5M/5M",
            "created": False,
        }

        result_customer, warning = (
            CustomerService
            .update_customer_connection(
                organization,
                "TEST001",
                {
                    "profile_name": (
                        "HomePlan"
                    ),
                },
            )
        )

        self.assertIs(
            result_customer,
            customer,
        )

        self.assertIsNone(
            warning
        )

        mock_provision.assert_called_once_with(
            customer,
            password=None,
            reset_password=False,
        )

        self.assertEqual(
            info.pppoe_pass,
            "existing-password",
        )

        info.save.assert_called_once()

    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "provision_pppoe_customer"
    )
    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "build_radius_username"
    )
    @patch(
        "customers.service."
        "CustomerProfile.objects.filter"
    )
    def test_radius_username_cannot_be_changed_manually(
        self,
        mock_filter,
        mock_build_username,
        mock_provision,
    ):
        (
            organization,
            customer,
            info,
        ) = self._build_customer()

        queryset = MagicMock()

        mock_filter.return_value = queryset

        (
            queryset
            .select_related
            .return_value
            .first
            .return_value
        ) = customer

        mock_build_username.return_value = (
            "lintech-demo-test001"
        )

        with self.assertRaises(
            serializers.ValidationError
        ):
            (
                CustomerService
                .update_customer_connection(
                    organization,
                    "TEST001",
                    {
                        "pppoe_name": (
                            "manual-username"
                        ),
                    },
                )
            )

        mock_provision.assert_not_called()

        info.save.assert_not_called()

    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "provision_pppoe_customer"
    )
    @patch(
        "radius.services."
        "RadiusProvisioningService."
        "build_radius_username"
    )
    @patch(
        "customers.service."
        "CustomerProfile.objects.filter"
    )
    def test_radius_password_cannot_be_empty(
        self,
        mock_filter,
        mock_build_username,
        mock_provision,
    ):
        (
            organization,
            customer,
            info,
        ) = self._build_customer()

        queryset = MagicMock()

        mock_filter.return_value = queryset

        (
            queryset
            .select_related
            .return_value
            .first
            .return_value
        ) = customer

        mock_build_username.return_value = (
            "lintech-demo-test001"
        )

        with self.assertRaises(
            serializers.ValidationError
        ):
            (
                CustomerService
                .update_customer_connection(
                    organization,
                    "TEST001",
                    {
                        "pppoe_pass": "",
                    },
                )
            )

        mock_provision.assert_not_called()

        info.save.assert_not_called()