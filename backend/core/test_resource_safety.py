from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet
from rest_framework.test import APIClient
from customers.models import AddressZone, CustomerProfile
from mikrotik.models import MikrotikRouter, RouterInfo
from olt.models import OltDevice, Onu
from organizations.models import Organization, OrganizationMembership


@override_settings(LINTECH_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class ResourceSafetyTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="ISP", slug="safe-isp")
        self.other = Organization.objects.create(name="Other", slug="safe-other")
        self.user = get_user_model().objects.create_user(username="safe-owner")
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role="owner")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.zone = AddressZone.objects.create(organization=self.org, name="Zone")
        self.customer = CustomerProfile.objects.create(organization=self.org, zone=self.zone, customer_id="C1", customer_name="Customer", phone_number="0712345678", address="Address")
        self.router = MikrotikRouter.objects.create(organization=self.org, name="Router", host="192.0.2.1", username="test", password="test")
        self.info = RouterInfo.objects.create(customer=self.customer, router=self.router, pppoe_name="subscriber", pppoe_pass="credential")
        self.olt = OltDevice.objects.create(organization=self.org, name="OLT", host="192.0.2.2", olt_type="GENERIC_EPON")
        self.other_olt = OltDevice.objects.create(organization=self.other, name="Other OLT", host="192.0.2.3", olt_type="GENERIC_EPON")

    def test_assigned_router_cannot_be_deleted(self):
        self.assertEqual(self.client.delete(f"/api/mikrotik/routers/{self.router.pk}/").status_code, 400)
        self.assertTrue(RouterInfo.objects.filter(pk=self.info.pk).exists())

    def test_assigned_zone_cannot_be_deleted(self):
        self.assertEqual(self.client.delete(f"/api/zones/{self.zone.pk}/").status_code, 400)
        self.assertTrue(CustomerProfile.objects.filter(pk=self.customer.pk).exists())

    def test_olt_with_onu_cannot_be_deleted(self):
        onu = Onu.objects.create(olt=self.olt, onu_index="1", serial_number="SERIAL")
        self.assertEqual(self.client.delete(f"/api/olt/devices/{self.olt.pk}/").status_code, 400)
        self.assertTrue(Onu.objects.filter(pk=onu.pk).exists())

    def test_cross_tenant_onu_create_and_update_fail_before_save(self):
        response = self.client.post("/api/olt/onus/", {"olt": self.other_olt.pk, "onu_index": "2", "name": "Forbidden"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Onu.objects.filter(name="Forbidden").exists())
        onu = Onu.objects.create(olt=self.olt, onu_index="1")
        response = self.client.patch(f"/api/olt/onus/{onu.pk}/", {"olt": self.other_olt.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        onu.refresh_from_db()
        self.assertEqual(onu.olt_id, self.olt.pk)

    def test_cross_tenant_customer_assignment_rejected(self):
        zone = AddressZone.objects.create(organization=self.other, name="Other")
        other_customer = CustomerProfile.objects.create(organization=self.other, zone=zone, customer_id="OTHER", customer_name="Other", phone_number="0712345678", address="Address")
        response = self.client.post("/api/olt/onus/", {"olt": self.olt.pk, "onu_index": "3", "customer": other_customer.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Onu.objects.filter(onu_index="3").exists())

    def test_unused_resources_can_still_be_deleted(self):
        zone = AddressZone.objects.create(organization=self.org, name="Empty")
        self.assertEqual(self.client.delete(f"/api/zones/{zone.pk}/").status_code, 204)
