from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from billing.models import Package
from customers.models import (
    AddressZone,
    CustomerProfile,
)
from customers.views import CustomerViewSet
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class CustomerRolePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

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

        self.zone = AddressZone.objects.create(
            organization=self.organization,
            name="Main Zone",
        )

        self.package = Package.objects.create(
            organization=self.organization,
            name="10 Mbps",
            package_type="monthly",
            speed="10 Mbps",
            price=Decimal("1000.00"),
            is_active=True,
        )

        self.customer = CustomerProfile.objects.create(
            organization=self.organization,
            customer_id="C001",
            customer_name="Test Customer",
            phone_number="0711000001",
            address="Test Address",
            zone=self.zone,
            package=self.package,
            customer_status="active",
            balance=Decimal("0.00"),
        )

        self.owner = self._create_user(
            "owner",
            "owner",
        )

        self.admin = self._create_user(
            "admin",
            "admin",
        )

        self.technician = self._create_user(
            "technician",
            "technician",
        )

        self.billing = self._create_user(
            "billing",
            "billing",
        )

        self.support = self._create_user(
            "support",
            "support",
        )

        self.viewer = self._create_user(
            "viewer",
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

    def test_viewer_can_list_customers(self):
        view = CustomerViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/customers/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_viewer_cannot_edit_customer(self):
        view = CustomerViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self._request(
            "patch",
            "/customers/C001/",
            self.viewer,
            {
                "customer_name": "Changed Name",
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.customer_name,
            "Test Customer",
        )

    def test_viewer_cannot_delete_customer(self):
        view = CustomerViewSet.as_view(
            {
                "delete": "destroy",
            }
        )

        request = self._request(
            "delete",
            "/customers/C001/",
            self.viewer,
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            CustomerProfile.objects.filter(
                pk=self.customer.pk
            ).exists()
        )

    @patch(
        "customers.views."
        "CustomerService.update_billing_settings"
    )
    def test_billing_user_can_update_billing_settings(
        self,
        mock_update,
    ):
        mock_update.return_value = self.customer

        view = CustomerViewSet.as_view(
            {
                "post": "update_billing",
            }
        )

        request = self._request(
            "post",
            "/customers/C001/update_billing/",
            self.billing,
            {
                "billing_day": 15,
                "extended_billing_days": 3,
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_update.assert_called_once_with(
            self.organization,
            self.customer.customer_id,
            15,
            3,
        )

    @patch(
        "customers.views."
        "CustomerService.update_billing_settings"
    )
    def test_technician_cannot_update_billing_settings(
        self,
        mock_update,
    ):
        view = CustomerViewSet.as_view(
            {
                "post": "update_billing",
            }
        )

        request = self._request(
            "post",
            "/customers/C001/update_billing/",
            self.technician,
            {
                "billing_day": 20,
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_update.assert_not_called()

    @patch(
        "customers.views."
        "CustomerService.get_customer_details"
    )
    @patch(
        "customers.views."
        "CustomerService.update_customer_connection"
    )
    def test_technician_can_update_customer_connection(
        self,
        mock_update_connection,
        mock_get_customer,
    ):
        mock_update_connection.return_value = (
            self.customer,
            None,
        )

        mock_get_customer.return_value = (
            self.customer
        )

        view = CustomerViewSet.as_view(
            {
                "post": "update_connection",
            }
        )

        request = self._request(
            "post",
            "/customers/C001/update_connection/",
            self.technician,
            {
                "profile_name": "10Mbps",
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_update_connection.assert_called_once()

    @patch(
        "customers.views."
        "CustomerService.update_customer_connection"
    )
    def test_support_user_cannot_update_customer_connection(
        self,
        mock_update_connection,
    ):
        view = CustomerViewSet.as_view(
            {
                "post": "update_connection",
            }
        )

        request = self._request(
            "post",
            "/customers/C001/update_connection/",
            self.support,
            {
                "profile_name": "10Mbps",
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_update_connection.assert_not_called()

    def test_admin_can_edit_customer(self):
        view = CustomerViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self._request(
            "patch",
            "/customers/C001/",
            self.admin,
            {
                "customer_name": (
                    "Updated Customer"
                ),
            },
        )

        response = view(
            request,
            customer_id=self.customer.customer_id,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.customer.refresh_from_db()

        self.assertEqual(
            self.customer.customer_name,
            "Updated Customer",
        )