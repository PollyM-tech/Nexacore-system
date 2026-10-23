"""Transactional registered-NAS subscriber status changes; no RouterOS admin API needed."""
from django.db import transaction
from rest_framework.exceptions import ValidationError
from customers.models import CustomerProfile
from .models import NasDevice
from .services import RadiusProvisioningService
from .disconnect import queue_customer


def set_status(customer, status):
    if status not in ('active', 'disconnected'):
        raise ValidationError('Unsupported subscriber status.')
    try:
        with transaction.atomic():
            customer = CustomerProfile.objects.select_for_update().get(pk=customer.pk)
            info = customer.router_info
            if not NasDevice.objects.filter(router_id=info.router_id, organization=customer.organization).exists():
                raise ValidationError('Register a NAS for this subscriber router before changing its RADIUS status.')
            customer.customer_status = status
            customer.save(update_fields=['customer_status', 'updated_at'])
            if status == 'active':
                RadiusProvisioningService.provision_pppoe_customer(customer, password=None, reset_password=False)
            else:
                RadiusProvisioningService.suspend_pppoe_customer(customer)
                queue_customer(customer)
            return customer, None
    except Exception:
        raise ValidationError('RADIUS status synchronization failed. No partial account status change was saved. Check the registered NAS and retry.') from None
