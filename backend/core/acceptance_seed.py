"""Disposable browser-test fixtures. Refuses any non-test database host."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings

if os.environ.get("LINTECH_ACCEPTANCE") != "1" or not settings.DATABASES["default"]["HOST"].startswith("lintech-test-db-"):
    raise SystemExit("Acceptance fixtures are restricted to disposable test databases.")

from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from billing.models import Package, PaymentTransaction, MonthlyBill
from customers.models import AddressZone, CustomerProfile
from mikrotik.models import RouterInfo
from organizations.models import Organization, OrganizationMembership
from radius.models import RadiusCheck, RadiusReply, RadAcct

with connection.schema_editor() as editor:
    existing = connection.introspection.table_names()
    for model in [RadiusCheck, RadiusReply, RadAcct]:
        if model._meta.db_table not in existing:
            editor.create_model(model)
password = os.environ["LINTECH_BROWSER_PASSWORD"]
User = get_user_model()
platform = User.objects.create_superuser(username="pilot-platform", email="platform@example.test", password=password, first_name="Pilot", last_name="Platform")
org = Organization.objects.create(name="Acceptance ISP", slug="acceptance")
for role in ["owner", "viewer", "technician", "billing", "support"]:
    user = User.objects.create(username=f"pilot-{role}", email=f"{role}@example.test", password=platform.password, first_name="Pilot", last_name=role.capitalize())
    OrganizationMembership.objects.create(user=user, organization=org, role=role)
OrganizationMembership.objects.create(user=platform, organization=org, role="owner")
zone = AddressZone.objects.create(organization=org, name="Acceptance Zone")
package = Package.objects.create(organization=org, name="Acceptance 10 Mbps", package_type="monthly", speed="10 Mbps", price="1500", is_active=True)
customer = CustomerProfile.objects.create(organization=org, zone=zone, package=package, customer_id="ACCEPT1", customer_name="Acceptance Customer", phone_number="0712345678", address="Acceptance Address", billing_date=timezone.localdate(), balance="-250")
RouterInfo.objects.create(customer=customer, pppoe_name="pilot-subscriber", pppoe_pass=password, authentication_mode="local_secret")
PaymentTransaction.objects.create(customer=customer, amount="1250", payment_method="cash", transaction_id="ACCEPTANCE-RECEIPT", received_by=platform)
today = timezone.localdate()
MonthlyBill.objects.create(customer=customer, package_name=package.name, package_price=package.price, billing_month=today.month, billing_year=today.year, invoice_date=today, total_amount="1500", paid_amount="1250", payment_status="partial")
other_org = Organization.objects.create(name="Other Acceptance ISP", slug="other-acceptance")
other_zone = AddressZone.objects.create(organization=other_org, name="Private Zone")
other_customer = CustomerProfile.objects.create(organization=other_org, zone=other_zone, customer_id="PRIVATE1", customer_name="Other Tenant Secret Name", phone_number="0712345679", address="Private Address")
PaymentTransaction.objects.create(customer=other_customer, amount="987654", payment_method="cash")
print("Disposable acceptance fixtures ready.")
