from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from customers.models import (
    AddressZone,
    CustomerProfile,
)
from organizations.models import (
    Organization,
    OrganizationMembership,
)
from sms.models import (
    SmsGateway,
    SmsLog,
    SmsTemplate,
)
from sms.providers import build_spec
from sms.recipients import resolve_recipients
from sms.service import SmsService
from sms.views import (
    SmsGatewayViewSet,
    SmsLogViewSet,
    SmsSendViewSet,
    SmsTemplateViewSet,
)


User = get_user_model()


class SmsTenantIsolationTests(TestCase):
    """
    Prove that SMS configuration, logs, recipients,
    and gateway usage cannot cross organization boundaries.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

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

        self.user_a = User.objects.create_user(
            username="alpha-admin",
            password="test-password",
        )

        self.user_b = User.objects.create_user(
            username="beta-admin",
            password="test-password",
        )

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role="owner",
            is_active=True,
        )

        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role="owner",
            is_active=True,
        )

        self.gateway_a = SmsGateway.objects.create(
            organization=self.org_a,
            provider="africastalking",
            label="Alpha SMS",
            sender_id="ALPHA",
            credentials={
                "username": "alpha",
                "api_key": "alpha-secret",
            },
            is_active=True,
            is_default=True,
        )

        self.gateway_b = SmsGateway.objects.create(
            organization=self.org_b,
            provider="africastalking",
            label="Beta SMS",
            sender_id="BETA",
            credentials={
                "username": "beta",
                "api_key": "beta-secret",
            },
            is_active=True,
            is_default=True,
        )

        self.template_a = SmsTemplate.objects.create(
            organization=self.org_a,
            name="Alpha Payment",
            category="payment",
            body="Payment received.",
        )

        self.template_b = SmsTemplate.objects.create(
            organization=self.org_b,
            name="Beta Payment",
            category="payment",
            body="Payment received.",
        )

        self.log_a = SmsLog.objects.create(
            organization=self.org_a,
            mobile="0711111111",
            message="Alpha message",
            provider="africastalking",
            status="sent",
        )

        self.log_b = SmsLog.objects.create(
            organization=self.org_b,
            mobile="0722222222",
            message="Beta message",
            provider="africastalking",
            status="sent",
        )

    def _list_response(
        self,
        viewset,
        user,
    ):
        view = viewset.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get("/")

        force_authenticate(
            request,
            user=user,
        )

        response = view(request)
        response.render()

        data = response.data

        if isinstance(data, dict):
            data = data.get(
                "results",
                [],
            )

        return data

    def test_gateway_list_is_scoped_to_organization(self):
        data = self._list_response(
            SmsGatewayViewSet,
            self.user_a,
        )

        ids = [
            item["id"]
            for item in data
        ]

        self.assertIn(
            self.gateway_a.id,
            ids,
        )

        self.assertNotIn(
            self.gateway_b.id,
            ids,
        )

    def test_template_list_is_scoped_to_organization(self):
        data = self._list_response(
            SmsTemplateViewSet,
            self.user_a,
        )

        ids = [
            item["id"]
            for item in data
        ]

        self.assertIn(
            self.template_a.id,
            ids,
        )

        self.assertNotIn(
            self.template_b.id,
            ids,
        )

    def test_sms_log_list_is_scoped_to_organization(self):
        data = self._list_response(
            SmsLogViewSet,
            self.user_a,
        )

        ids = [
            item["id"]
            for item in data
        ]

        self.assertIn(
            self.log_a.id,
            ids,
        )

        self.assertNotIn(
            self.log_b.id,
            ids,
        )

    def test_cannot_send_using_foreign_gateway(self):
        with self.assertRaises(ValueError):
            SmsService.send_one(
                organization=self.org_a,
                mobile="0712345678",
                message="Test message",
                gateway=self.gateway_b,
                user=self.user_a,
            )

    def test_default_gateway_isolated_per_organization(self):
        second_alpha_gateway = (
            SmsGateway.objects.create(
                organization=self.org_a,
                provider="africastalking",
                label="Alpha Backup",
                sender_id="ALPHA2",
                credentials={},
                is_active=True,
                is_default=True,
            )
        )

        self.gateway_a.refresh_from_db()
        self.gateway_b.refresh_from_db()
        second_alpha_gateway.refresh_from_db()

        self.assertFalse(
            self.gateway_a.is_default
        )

        self.assertTrue(
            second_alpha_gateway.is_default
        )

        self.assertTrue(
            self.gateway_b.is_default
        )

    def test_gateway_credentials_are_not_returned(self):
        data = self._list_response(
            SmsGatewayViewSet,
            self.user_a,
        )

        self.assertEqual(
            len(data),
            1,
        )

        self.assertNotIn(
            "credentials",
            data[0],
        )


class SmsRecipientTenantIsolationTests(TestCase):
    """
    Recipient selection must never return customers
    from another organization.
    """

    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Recipient ISP Alpha",
            slug="recipient-isp-alpha",
            organization_type="pppoe",
            status="active",
            is_active=True,
        )

        self.org_b = Organization.objects.create(
            name="Recipient ISP Beta",
            slug="recipient-isp-beta",
            organization_type="pppoe",
            status="active",
            is_active=True,
        )

        self.zone_a = AddressZone.objects.create(
            organization=self.org_a,
            name="Alpha Zone",
        )

        self.zone_b = AddressZone.objects.create(
            organization=self.org_b,
            name="Beta Zone",
        )

        self.customer_a = CustomerProfile.objects.create(
            organization=self.org_a,
            customer_id="CUST-001",
            customer_name="Alpha Customer",
            phone_number="0711111111",
            customer_status="active",
            zone=self.zone_a,
        )

        self.customer_b = CustomerProfile.objects.create(
            organization=self.org_b,
            customer_id="CUST-001",
            customer_name="Beta Customer",
            phone_number="0722222222",
            customer_status="active",
            zone=self.zone_b,
        )

    def test_customer_lookup_is_scoped_to_organization(self):
        recipients = resolve_recipients(
            self.org_a,
            "customer",
            {
                "customer_id": "CUST-001",
            },
        )

        self.assertEqual(
            len(recipients),
            1,
        )

        mobile, customer = recipients[0]

        self.assertEqual(
            mobile,
            self.customer_a.phone_number,
        )

        self.assertEqual(
            customer.id,
            self.customer_a.id,
        )

        self.assertNotEqual(
            customer.id,
            self.customer_b.id,
        )

    def test_bulk_active_audience_excludes_other_organization(self):
        recipients = resolve_recipients(
            self.org_a,
            "active",
            {},
        )

        customer_ids = [
            customer.id
            for _, customer in recipients
        ]

        self.assertIn(
            self.customer_a.id,
            customer_ids,
        )

        self.assertNotIn(
            self.customer_b.id,
            customer_ids,
        )


class AfricaTalkingProviderTests(TestCase):
    def test_sandbox_request_spec(self):
        spec = build_spec(
            "africastalking",
            {
                "username": "sandbox",
                "api_key": "test-key",
                "environment": "sandbox",
                "sender_id": "LINTECH",
            },
            "+254712345678",
            "Test message",
        )

        self.assertEqual(
            spec.url,
            (
                "https://api.sandbox."
                "africastalking.com/version1/messaging"
            ),
        )

        self.assertEqual(
            spec.method,
            "post",
        )

        self.assertEqual(
            spec.headers["apiKey"],
            "test-key",
        )

        self.assertEqual(
            spec.headers["Accept"],
            "application/json",
        )

        self.assertEqual(
            spec.headers["Content-Type"],
            "application/x-www-form-urlencoded",
        )

        self.assertEqual(
            spec.data["username"],
            "sandbox",
        )

        self.assertEqual(
            spec.data["to"],
            "+254712345678",
        )

        self.assertEqual(
            spec.data["message"],
            "Test message",
        )

        self.assertEqual(
            spec.data["from"],
            "LINTECH",
        )

    def test_live_request_spec(self):
        spec = build_spec(
            "africastalking",
            {
                "username": "lintech-live",
                "api_key": "live-test-key",
                "environment": "live",
            },
            "+254700000001",
            "Live message",
        )

        self.assertEqual(
            spec.url,
            (
                "https://api."
                "africastalking.com/version1/messaging"
            ),
        )

        self.assertEqual(
            spec.method,
            "post",
        )

        self.assertEqual(
            spec.data["username"],
            "lintech-live",
        )

        self.assertEqual(
            spec.data["to"],
            "+254700000001",
        )

        self.assertEqual(
            spec.data["message"],
            "Live message",
        )

    def test_sender_id_is_optional(self):
        spec = build_spec(
            "africastalking",
            {
                "username": "sandbox",
                "api_key": "test-key",
                "environment": "sandbox",
            },
            "+254711111111",
            "No sender ID",
        )

        self.assertNotIn(
            "from",
            spec.data,
        )

    def test_default_environment_is_sandbox(self):
        spec = build_spec(
            "africastalking",
            {
                "username": "sandbox",
                "api_key": "test-key",
            },
            "+254722222222",
            "Default environment",
        )

        self.assertEqual(
            spec.url,
            (
                "https://api.sandbox."
                "africastalking.com/version1/messaging"
            ),
        )

    def test_unknown_provider_fails(self):
        with self.assertRaises(ValueError):
            build_spec(
                "does-not-exist",
                {},
                "+254733333333",
                "Unknown provider",
            )


class SmsRolePermissionTests(TestCase):
    """
    Verify SMS role-based access control.

    Gateway administration is owner/admin only.
    Billing can manage templates and send SMS.
    Support can send SMS.
    Technician and viewer cannot send SMS.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="SMS Role Test ISP",
            slug="sms-role-test-isp",
            organization_type="hybrid",
            status="active",
            is_active=True,
        )

        self.gateway = SmsGateway.objects.create(
            organization=self.organization,
            provider="africastalking",
            label="Test Gateway",
            sender_id="LINTECH",
            credentials={
                "username": "sandbox",
                "api_key": "test-key",
            },
            is_active=True,
            is_default=True,
        )

        self.owner = self._create_user(
            "sms_owner",
            "owner",
        )

        self.billing = self._create_user(
            "sms_billing",
            "billing",
        )

        self.support = self._create_user(
            "sms_support",
            "support",
        )

        self.technician = self._create_user(
            "sms_technician",
            "technician",
        )

        self.viewer = self._create_user(
            "sms_viewer",
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

    def test_viewer_can_read_sms_logs(self):
        SmsLog.objects.create(
            organization=self.organization,
            mobile="0712345678",
            message="Test log",
            provider="africastalking",
            status="sent",
        )

        view = SmsLogViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self._request(
            "get",
            "/sms/logs/",
            self.viewer,
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_billing_user_can_create_template(self):
        view = SmsTemplateViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/sms/templates/",
            self.billing,
            {
                "name": "Payment Reminder",
                "category": "payment",
                "body": "Your payment is due.",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            SmsTemplate.objects.filter(
                organization=self.organization,
                name="Payment Reminder",
            ).exists()
        )

    def test_technician_cannot_create_template(self):
        view = SmsTemplateViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self._request(
            "post",
            "/sms/templates/",
            self.technician,
            {
                "name": "Blocked Template",
                "category": "payment",
                "body": "This should not be created.",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            SmsTemplate.objects.filter(
                organization=self.organization,
                name="Blocked Template",
            ).exists()
        )

    @patch(
        "sms.views.SmsService.send_one"
    )
    def test_billing_user_cannot_test_gateway(
        self,
        mock_send_one,
    ):
        view = SmsGatewayViewSet.as_view(
            {
                "post": "test",
            }
        )

        request = self._request(
            "post",
            f"/sms/gateways/{self.gateway.pk}/test/",
            self.billing,
            {
                "mobile": "0712345678",
                "message": "Gateway test",
            },
        )

        response = view(
            request,
            pk=self.gateway.pk,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_send_one.assert_not_called()

    @patch(
        "sms.views.SmsService.send_bulk"
    )
    @patch(
        "sms.views.resolve_recipients"
    )
    def test_support_user_can_send_sms(
        self,
        mock_resolve_recipients,
        mock_send_bulk,
    ):
        mock_resolve_recipients.return_value = [
            (
                "0712345678",
                None,
            )
        ]

        mock_send_bulk.return_value = {
            "status": "success",
            "sent": 1,
            "failed": 0,
        }

        view = SmsSendViewSet.as_view(
            {
                "post": "send",
            }
        )

        request = self._request(
            "post",
            "/sms/send/",
            self.support,
            {
                "audience": "active",
                "message": "Service notice",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_resolve_recipients.assert_called_once()

        mock_send_bulk.assert_called_once()

        call_kwargs = (
            mock_send_bulk.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["organization"],
            self.organization,
        )

        self.assertEqual(
            call_kwargs["user"],
            self.support,
        )

    @patch(
        "sms.views.SmsService.send_bulk"
    )
    @patch(
        "sms.views.resolve_recipients"
    )
    def test_technician_cannot_send_sms(
        self,
        mock_resolve_recipients,
        mock_send_bulk,
    ):
        view = SmsSendViewSet.as_view(
            {
                "post": "send",
            }
        )

        request = self._request(
            "post",
            "/sms/send/",
            self.technician,
            {
                "audience": "active",
                "message": "Blocked message",
            },
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            403,
        )

        mock_resolve_recipients.assert_not_called()
        mock_send_bulk.assert_not_called()