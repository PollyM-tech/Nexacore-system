"""Profile API package updates synchronize the real test RADIUS tables."""
from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from auditlog.models import AuditLog
from billing.models import Package
from customers.models import AddressZone, CustomerProfile
from customers.service import CustomerService
from mikrotik.models import MikrotikRouter, RouterInfo
from organizations.models import Organization, OrganizationMembership
from radius.models import RadiusCheck, RadiusReply
from radius.services import RadiusProvisioningService


@override_settings(LINTECH_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class RadiusPackageSyncTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # These unmanaged tables are created only in the isolated test DB.
        cls.created_models = []
        existing = connection.introspection.table_names()
        with connection.schema_editor() as editor:
            for model in (RadiusCheck, RadiusReply):
                if model._meta.db_table not in existing:
                    editor.create_model(model)
                    cls.created_models.append(model)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            for model in reversed(cls.created_models):
                editor.delete_model(model)

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Package ISP", slug="package-isp", is_active=True)
        cls.other = Organization.objects.create(name="Other ISP", slug="other-package-isp", is_active=True)
        cls.user = get_user_model().objects.create_user(username="package-admin")
        OrganizationMembership.objects.create(organization=cls.org, user=cls.user, role="owner", is_active=True)
        cls.zone = AddressZone.objects.create(organization=cls.org, name="Zone")
        cls.old_package = Package.objects.create(
            organization=cls.org, name="5 Mbps", speed="5 Mbps", price=Decimal("500"), is_active=True,
        )
        cls.new_package = Package.objects.create(
            organization=cls.org, name="10 Mbps", speed="10 Mbps", price=Decimal("1000"), is_active=True,
        )
        cls.router = MikrotikRouter.objects.create(
            organization=cls.org, name="Router", host="10.0.0.1", username="admin", password="router-password",
        )
        cls.password = "Customer-secret-unchanged"
        cls.customer = CustomerService.create_customer(cls.org, {
            "customer_id": "PKG1", "customer_name": "Customer", "phone_number": "0711000000",
            "address": "Address", "zone_id": cls.zone.pk, "package_id": cls.old_package.pk,
            "router_id": cls.router.pk, "authentication_mode": "radius", "pppoe_pass": cls.password,
        })
        cls.username = cls.customer.router_info.pppoe_name

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/customers/{self.customer.customer_id}/"

    def update(self, package, **fields):
        return self.client.patch(self.url, {"package": package, **fields}, format="json")

    def assert_original(self):
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.package_id, self.old_package.pk)
        self.assertEqual(RadiusReply.objects.get(attribute="Mikrotik-Rate-Limit").value, "5M/5M")
        self.assert_credentials_preserved()

    def assert_credentials_preserved(self):
        info = RouterInfo.objects.get(customer=self.customer)
        self.assertEqual(info.pppoe_name, self.username)
        self.assertEqual(info.pppoe_pass, self.password)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").username, self.username)

    def test_patch_updates_package_rate_limit_and_preserves_credentials(self):
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer", wraps=RadiusProvisioningService.provision_pppoe_customer) as provision, patch.object(RadiusProvisioningService, "_generate_password") as generate:
            response = self.update(self.new_package.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.package_id, self.new_package.pk)
        self.assertEqual(response.data["package"], self.new_package.pk)
        self.assertEqual(response.data["package_name"], self.new_package.name)
        self.assertEqual(RadiusReply.objects.get(attribute="Mikrotik-Rate-Limit").value, "10M/10M")
        provision.assert_called_once_with(self.customer, password=None, reset_password=False)
        generate.assert_not_called()
        self.assert_credentials_preserved()
        self.assertNotIn(self.password, response.content.decode())
        self.assertNotIn("pppoe_pass", response.content.decode())
        audit = AuditLog.objects.get(action="customer.updated")
        self.assertEqual(audit.metadata["before"]["package_id"], self.old_package.pk)
        self.assertEqual(audit.metadata["after"]["package_id"], self.new_package.pk)
        self.assertNotIn(self.password, str(audit.metadata))

    def test_put_updates_rate_limit(self):
        response = self.client.put(self.url, {
            "customer_name": "Customer", "phone_number": "0711000000", "address": "Address",
            "zone": self.zone.pk, "package": self.new_package.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(RadiusReply.objects.get(attribute="Mikrotik-Rate-Limit").value, "10M/10M")
        self.assert_credentials_preserved()

    def test_inactive_package_rejected(self):
        self.new_package.is_active = False
        self.new_package.save()
        self.assertEqual(self.update(self.new_package.pk).status_code, 400)
        self.assert_original()

    def test_other_organization_package_rejected(self):
        other_package = Package.objects.create(organization=self.other, name="Other", speed="50 Mbps", price=100)
        self.assertEqual(self.update(other_package.pk).status_code, 400)
        self.assert_original()

    def test_nonexistent_package_rejected(self):
        self.assertEqual(self.update(max(self.old_package.pk, self.new_package.pk) + 999).status_code, 400)
        self.assert_original()

    def test_invalid_speed_rejected_and_entire_profile_rolled_back(self):
        for speed in ("", "unsupported-speed"):
            with self.subTest(speed=speed):
                self.new_package.speed = speed
                self.new_package.save()
                response = self.update(self.new_package.pk, customer_name="Must roll back")
                self.assertEqual(response.status_code, 400)
                self.assert_original()
                self.assertEqual(self.customer.customer_name, "Customer")
                self.assertFalse(AuditLog.objects.filter(action="customer.updated").exists())

    def test_package_cannot_be_cleared(self):
        self.assertEqual(self.update(None).status_code, 400)
        self.assert_original()

    def test_failure_after_radius_write_rolls_back_everything(self):
        original = RadiusProvisioningService.provision_pppoe_customer
        def fail_after_write(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError(self.password)
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer", side_effect=fail_after_write):
            response = self.update(self.new_package.pk, customer_name="Must roll back")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.password, response.content.decode())
        self.assert_original()
        self.assertEqual(self.customer.customer_name, "Customer")
        self.assertFalse(AuditLog.objects.filter(action="customer.updated").exists())

    def test_profile_only_edit_does_not_reprovision(self):
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer") as provision:
            response = self.client.patch(self.url, {"customer_name": "Updated"}, format="json")
        self.assertEqual(response.status_code, 200)
        provision.assert_not_called()
        self.assert_original()
        self.assertEqual(self.customer.customer_name, "Updated")

    def test_same_package_does_not_reprovision(self):
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer") as provision:
            response = self.update(self.old_package.pk)
        self.assertEqual(response.status_code, 200)
        provision.assert_not_called()
        self.assert_original()

    def test_local_secret_behavior_unchanged(self):
        RouterInfo.objects.filter(customer=self.customer).update(authentication_mode="local_secret")
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer") as provision, patch("mikrotik.service.helpers.update_pppoe_secret_on_router") as router_update:
            self.assertEqual(self.update(self.new_package.pk).status_code, 200)
            self.assertEqual(self.update(None).status_code, 200)
        provision.assert_not_called()
        router_update.assert_not_called()
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.package_id)

    def test_profile_without_connection_can_change_and_clear_package(self):
        RouterInfo.objects.filter(customer=self.customer).delete()
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer") as provision:
            self.assertEqual(self.update(self.new_package.pk).status_code, 200)
            self.assertEqual(self.update(None).status_code, 200)
        provision.assert_not_called()

    def test_missing_radius_password_rejects_without_generating(self):
        RadiusCheck.objects.filter(attribute="Cleartext-Password").delete()
        with patch.object(RadiusProvisioningService, "_generate_password") as generate:
            response = self.update(self.new_package.pk)
        self.assertEqual(response.status_code, 400)
        generate.assert_not_called()
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.package_id, self.old_package.pk)

    def test_change_does_not_disconnect_active_session(self):
        with patch("mikrotik.service.helpers.disconnect_pppoe_session_on_router") as disconnect:
            self.assertEqual(self.update(self.new_package.pk).status_code, 200)
        disconnect.assert_not_called()

    def test_inconsistent_username_requires_repair(self):
        RouterInfo.objects.filter(customer=self.customer).update(pppoe_name="inconsistent")
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer") as provision:
            self.assertEqual(self.update(self.new_package.pk).status_code, 400)
        provision.assert_not_called()
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.package_id, self.old_package.pk)

    def test_credential_lookup_failure_returns_safe_error(self):
        with patch.object(RadiusCheck.objects, "select_for_update", side_effect=RuntimeError(self.password)):
            response = self.update(self.new_package.pk)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.password, response.content.decode())
        self.assert_original()
