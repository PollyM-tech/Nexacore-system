from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
)

from auditlog.models import AuditLog
from auditlog.services import AuditService
from organizations.models import (
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class AuditLogFoundationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.org_a = Organization.objects.create(
            name="Audit ISP A",
            slug="audit-isp-a",
            organization_type="hybrid",
            status="active",
            is_active=True,
        )

        self.org_b = Organization.objects.create(
            name="Audit ISP B",
            slug="audit-isp-b",
            organization_type="hybrid",
            status="active",
            is_active=True,
        )

        self.owner_a = self._create_user(
            "audit_owner_a",
            "owner",
            self.org_a,
        )

        self.admin_a = self._create_user(
            "audit_admin_a",
            "admin",
            self.org_a,
        )

        self.viewer_a = self._create_user(
            "audit_viewer_a",
            "viewer",
            self.org_a,
        )

        self.owner_b = self._create_user(
            "audit_owner_b",
            "owner",
            self.org_b,
        )

    def _create_user(
        self,
        username,
        role,
        organization,
    ):
        user = User.objects.create_user(
            username=username,
            password="testpass123",
        )

        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=role,
            is_active=True,
        )

        return user

    def test_service_creates_audit_record(self):
        log = AuditService.log(
            organization=self.org_a,
            user=self.owner_a,
            action="customer.status_changed",
            resource_type="CustomerProfile",
            resource_id="C001",
            description=(
                "Customer disconnected."
            ),
            metadata={
                "old_status": "active",
                "new_status": "disconnected",
            },
        )

        self.assertEqual(
            log.organization,
            self.org_a,
        )

        self.assertEqual(
            log.user,
            self.owner_a,
        )

        self.assertEqual(
            log.actor_role,
            "owner",
        )

        self.assertEqual(
            log.action,
            "customer.status_changed",
        )

    def test_sensitive_metadata_is_redacted(self):
        log = AuditService.log(
            organization=self.org_a,
            user=self.owner_a,
            action="router.updated",
            resource_type="MikrotikRouter",
            resource_id="10",
            metadata={
                "host": "10.0.0.1",
                "password": "secret-password",
                "credentials": {
                    "username": "admin",
                    "api_key": "secret-key",
                },
            },
        )

        self.assertEqual(
            log.metadata["host"],
            "10.0.0.1",
        )

        self.assertEqual(
            log.metadata["password"],
            "[REDACTED]",
        )

        self.assertEqual(
            log.metadata["credentials"],
            "[REDACTED]",
        )

    def test_request_information_is_recorded(self):
        request = self.factory.post(
            "/api/customers/C001/update_status/",
            {
                "status": "disconnected",
            },
            format="json",
            REMOTE_ADDR="10.10.10.5",
            HTTP_USER_AGENT="Lintech Test Client",
        )

        request.user = self.owner_a

        log = AuditService.log(
            organization=self.org_a,
            request=request,
            action="customer.status_changed",
            resource_type="CustomerProfile",
            resource_id="C001",
        )

        self.assertEqual(
            log.user,
            self.owner_a,
        )

        self.assertEqual(
            log.request_method,
            "POST",
        )

        self.assertEqual(
            log.request_path,
            "/api/customers/C001/update_status/",
        )

        self.assertEqual(
            str(log.ip_address),
            "10.10.10.5",
        )

        self.assertEqual(
            log.user_agent,
            "Lintech Test Client",
        )

    def test_owner_only_sees_own_organization_logs(self):
        AuditService.log(
            organization=self.org_a,
            user=self.owner_a,
            action="customer.updated",
            resource_type="CustomerProfile",
            resource_id="A001",
        )

        AuditService.log(
            organization=self.org_b,
            user=self.owner_b,
            action="customer.updated",
            resource_type="CustomerProfile",
            resource_id="B001",
        )

        client = APIClient()

        client.force_authenticate(
            self.owner_a
        )

        response = client.get(
            "/api/audit/logs/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.data

        if isinstance(data, dict):
            data = data.get(
                "results",
                [],
            )

        resource_ids = [
            item["resource_id"]
            for item in data
        ]

        self.assertIn(
            "A001",
            resource_ids,
        )

        self.assertNotIn(
            "B001",
            resource_ids,
        )

    def test_admin_can_view_audit_logs(self):
        AuditService.log(
            organization=self.org_a,
            user=self.owner_a,
            action="package.updated",
            resource_type="Package",
            resource_id="1",
        )

        client = APIClient()

        client.force_authenticate(
            self.admin_a
        )

        response = client.get(
            "/api/audit/logs/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_viewer_cannot_view_audit_logs(self):
        client = APIClient()

        client.force_authenticate(
            self.viewer_a
        )

        response = client.get(
            "/api/audit/logs/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_platform_event_can_have_no_organization(self):
        superuser = User.objects.create_superuser(
            username="audit_platform_admin",
            email="platform@example.com",
            password="testpass123",
        )

        log = AuditService.log(
            organization=None,
            user=superuser,
            action="scheduler.enabled",
            resource_type="Schedule",
            resource_id="monthly-billing",
        )

        self.assertIsNone(
            log.organization
        )

        self.assertEqual(
            log.actor_role,
            "platform_admin",
        )