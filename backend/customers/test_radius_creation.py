"""Operator-supplied RADIUS passwords remain write-only throughout the API."""
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
from customers.serializers.customer_create import CustomerCreateSerializer
from customers.service import CustomerService
from mikrotik.models import MikrotikRouter, RouterInfo
from organizations.models import Organization, OrganizationMembership
from radius.models import RadiusCheck, RadiusReply
from radius.services import RadiusProvisioningError, RadiusProvisioningService


@override_settings(LINTECH_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class RadiusCreationWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # FreeRADIUS owns these unmanaged tables in production. Create only
        # missing tables in the isolated test database, without a migration.
        existing = connection.introspection.table_names()
        cls.created_models = []
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
        cls.org = Organization.objects.create(name="Install ISP", slug="install-isp", is_active=True)
        cls.zone = AddressZone.objects.create(organization=cls.org, name="Zone")
        cls.package = Package.objects.create(
            organization=cls.org, name="Home", speed="10 Mbps",
            price=Decimal("1000"), is_active=True,
        )
        cls.router = MikrotikRouter.objects.create(
            organization=cls.org, name="Router", host="10.0.0.1",
            username="admin", password="router-test-password",
        )
        cls.user = get_user_model().objects.create_user(username="installer")
        OrganizationMembership.objects.create(organization=cls.org, user=cls.user, role="owner", is_active=True)
        cls.other_org = Organization.objects.create(name="Other", slug="other-installer", is_active=True)
        cls.other_user = get_user_model().objects.create_user(username="other-installer")
        OrganizationMembership.objects.create(organization=cls.other_org, user=cls.other_user, role="owner", is_active=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.password = "  Customer-chosen-Secret!  "
        self.payload = {
            "customer_id": "INSTALL1", "customer_name": "Customer",
            "phone_number": "0711000000", "address": "Test address",
            "zone_id": self.zone.pk, "package_id": self.package.pk,
            "router_id": self.router.pk, "authentication_mode": "radius",
            "pppoe_pass": self.password,
        }

    def create_customer(self):
        response = self.client.post("/api/customers/", self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return CustomerProfile.objects.get(customer_id="INSTALL1"), response

    def assert_password_free(self, response, *passwords):
        content = response.content.decode()
        for marker in ("pppoe_pass", "password", "Cleartext-Password", "lintech:v1:", *passwords):
            self.assertNotIn(marker, content)

    def test_radius_creation_requires_password(self):
        self.payload.pop("pppoe_pass")
        response = self.client.post("/api/customers/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("pppoe_pass", response.data)
        self.assertFalse(CustomerProfile.objects.exists())

    def test_blank_and_whitespace_passwords_rejected(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                self.payload["pppoe_pass"] = value
                response = self.client.post("/api/customers/", self.payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("pppoe_pass", response.data)
        self.assertFalse(CustomerProfile.objects.exists())

    def test_generated_username_and_exact_supplied_password_provisioned(self):
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer", wraps=RadiusProvisioningService.provision_pppoe_customer) as provision, patch.object(RadiusProvisioningService, "_generate_password") as generate:
            customer, response = self.create_customer()
        provision.assert_called_once_with(customer, password=self.password, reset_password=True)
        generate.assert_not_called()
        info = customer.router_info
        self.assertEqual(info.pppoe_name, "install-isp-install1")
        self.assertEqual(info.pppoe_pass, self.password)
        self.assertEqual(RadiusCheck.objects.get(username=info.pppoe_name, attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RadiusReply.objects.get(username=info.pppoe_name, attribute="Mikrotik-Rate-Limit").value, "10M/10M")
        self.assertEqual(response.data["router_info"]["authentication_mode"], "radius")
        self.assertEqual(response.data["router_info"]["pppoe_name"], info.pppoe_name)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pppoe_pass FROM mikrotik_routerinfo WHERE id = %s", [info.pk])
            stored = cursor.fetchone()[0]
        self.assertTrue(stored.startswith("lintech:v1:"))
        self.assertNotIn(self.password, stored)

    def test_supplied_username_explicitly_rejected(self):
        self.payload["pppoe_name"] = "client-selected-name"
        response = self.client.post("/api/customers/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("pppoe_name", response.data)
        self.assertFalse(CustomerProfile.objects.exists())

    def test_create_detail_and_list_do_not_return_passwords(self):
        customer, created = self.create_customer()
        detail = self.client.get(f"/api/customers/{customer.customer_id}/")
        listing = self.client.get("/api/customers/")
        for response in (created, detail, listing):
            self.assertLess(response.status_code, 300)
            self.assert_password_free(response, self.password)
        self.assertNotIn(self.password, str(list(AuditLog.objects.values())))

    def test_password_change_updates_radius_and_encrypted_copy(self):
        customer, _ = self.create_customer()
        new_password = "  Explicit-new-password!  "
        response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"pppoe_pass": new_password}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        info = RouterInfo.objects.get(customer=customer)
        self.assertEqual(info.pppoe_name, "install-isp-install1")
        self.assertEqual(info.pppoe_pass, new_password)
        self.assertEqual(RadiusCheck.objects.get(username=info.pppoe_name, attribute="Cleartext-Password").value, new_password)
        self.assert_password_free(response, new_password, self.password)
        self.assertNotIn(new_password, str(list(AuditLog.objects.values())))

    def test_omitted_password_retains_existing(self):
        customer, _ = self.create_customer()
        response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"profile_name": "Home"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RouterInfo.objects.get(customer=customer).pppoe_pass, self.password)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)

    def test_blank_password_changes_rejected(self):
        customer, _ = self.create_customer()
        for value in ("", "   ", None, 123):
            response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"pppoe_pass": value}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RouterInfo.objects.get(customer=customer).pppoe_pass, self.password)

    def test_generated_username_cannot_be_changed(self):
        customer, _ = self.create_customer()
        response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"pppoe_name": "override", "pppoe_pass": "new-password"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)

    def test_other_tenant_cannot_modify_credentials(self):
        customer, _ = self.create_customer()
        self.client.force_authenticate(self.other_user)
        response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"pppoe_pass": "other-tenant-password"}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RouterInfo.objects.get(customer=customer).pppoe_pass, self.password)

    def test_profile_and_package_patch_do_not_change_password(self):
        customer, _ = self.create_customer()
        response = self.client.patch(f"/api/customers/{customer.customer_id}/", {"customer_name": "Updated", "package": self.package.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RouterInfo.objects.get(customer=customer).pppoe_pass, self.password)

    def test_creation_failure_rolls_back_and_does_not_echo_secret(self):
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer", side_effect=RadiusProvisioningError(self.password)):
            response = self.client.post("/api/customers/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.password, response.content.decode())
        self.assertFalse(CustomerProfile.objects.exists())
        self.assertFalse(RouterInfo.objects.exists())

    def test_update_failure_rolls_back_and_does_not_echo_secret(self):
        customer, _ = self.create_customer()
        original = RadiusProvisioningService.provision_pppoe_customer
        def fail_after_write(*args, **kwargs):
            original(*args, **kwargs)
            raise RadiusProvisioningError("new-secret")
        with patch.object(RadiusProvisioningService, "provision_pppoe_customer", side_effect=fail_after_write):
            response = self.client.post(f"/api/customers/{customer.customer_id}/update_connection/", {"pppoe_pass": "new-secret"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("new-secret", response.content.decode())
        self.assertEqual(RadiusCheck.objects.get(attribute="Cleartext-Password").value, self.password)
        self.assertEqual(RouterInfo.objects.get(customer=customer).pppoe_pass, self.password)

    def test_service_rejects_missing_password_without_serializer(self):
        self.payload.pop("pppoe_pass")
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            CustomerService.create_customer(self.org, self.payload)
        self.assertFalse(CustomerProfile.objects.exists())

    def test_local_secret_creation_unchanged_and_password_free(self):
        self.payload.update(authentication_mode="local_secret", pppoe_name="INSTALL-LOCAL", pppoe_pass="local-secret")
        with patch("mikrotik.service.helpers.check_pppoe_user_exists_on_router", return_value=None), patch("mikrotik.service.helpers.create_pppoe_user_on_router") as create:
            customer, response = self.create_customer()
        self.assertEqual(customer.router_info.pppoe_name, "install-local")
        self.assertEqual(customer.router_info.pppoe_pass, "local-secret")
        self.assertEqual(create.call_args.kwargs["pppoe_pass"], "local-secret")
        self.assert_password_free(response, "local-secret")
        self.assert_password_free(self.client.get(f"/api/customers/{customer.customer_id}/"), "local-secret")
        self.assert_password_free(self.client.get("/api/customers/"), "local-secret")

    def test_local_secret_credentials_still_required_with_router(self):
        for field in ("pppoe_name", "pppoe_pass"):
            payload = {**self.payload, "authentication_mode": "local_secret", "pppoe_name": "local"}
            payload.pop(field)
            serializer = CustomerCreateSerializer(data=payload)
            self.assertFalse(serializer.is_valid())
            self.assertIn(field, serializer.errors)
