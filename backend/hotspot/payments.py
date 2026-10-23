"""Subscriber hotspot purchases, separate from Lintech SaaS subscription billing."""
import secrets
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError
from payments.models import PaymentAttempt, MpesaConfiguration
from payments.services.stk import StkPushService
from billing.models import PaymentTransaction
from auditlog.services import AuditService
from .models import HotspotPurchase, HotspotSale
from .services import digest, snapshot


def start_purchase(nas, plan, phone, request_id):
    if not getattr(settings, 'RADIUS_ISOLATED', False) or len(getattr(settings, 'RADIUS_INTERNAL_TOKEN', '')) < 32:
        raise ValidationError('Voucher purchases are disabled until registered-NAS RADIUS is enabled.')
    phone = StkPushService.normalize_phone_number(phone)
    if not nas.is_active or not nas.hotspot_enabled or not nas.organization.is_active or nas.organization.status != 'active':
        raise ValidationError('NAS unavailable.')
    if plan.organization_id != nas.organization_id or not plan.is_active:
        raise ValidationError('Plan unavailable.')
    configurations = MpesaConfiguration.objects.filter(organization=nas.organization, is_active=True, is_default=True)
    configuration = configurations.filter(service_scope='hotspot').first() or configurations.filter(service_scope='both').first()
    base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    if not configuration or not base.startswith('https://'):
        raise ValidationError('Online purchase is not configured. Obtain a voucher from your ISP.')
    phone_hash = digest(phone)
    with transaction.atomic():
        # Serialize initiation only until durable intent creation; never hold DB locks over Daraja I/O.
        type(nas).objects.select_for_update().get(pk=nas.pk)
        purchase = HotspotPurchase.objects.filter(request_id=request_id).first()
        if purchase:
            if purchase.nas_id != nas.pk or purchase.plan_id != plan.pk or purchase.phone_hash != phone_hash:
                raise ValidationError('Purchase retry does not match the original request.')
            return purchase, purchase.recovery_token
        from django.core.cache import cache
        from django.utils import timezone
        from datetime import timedelta
        if HotspotPurchase.objects.filter(phone_hash=phone_hash, created_at__gte=timezone.now()-timedelta(hours=1)).count() >= 5:
            raise ValidationError('Too many payment requests for this phone. Check previous prompts or contact your ISP.')
        if not cache.add('hotspot-phone-' + phone_hash, True, timeout=60):
            raise ValidationError('A payment prompt was recently requested for this phone. Wait before retrying.')
        token = secrets.token_urlsafe(32)
        purchase = HotspotPurchase.objects.create(nas=nas, plan=plan, price=plan.price,
            token_hash=digest(token), recovery_token=token, request_id=request_id, phone_hash=phone_hash, entitlement=snapshot(plan))
        attempt = PaymentAttempt.objects.create(organization=nas.organization, payment_configuration=configuration,
            phone_number=phone, amount=plan.price, account_reference='HS'+purchase.pk.hex[:10],
            service_type='hotspot', purpose='hotspot_purchase')
        purchase.attempt = attempt
        purchase.save(update_fields=['attempt'])
    try:
        result = StkPushService(configuration).initiate(phone_number=phone, amount=plan.price,
            account_reference=attempt.account_reference, callback_url=f'{base}/hooks/stk/{configuration.callback_token}/result/')
        attempt.merchant_request_id = result['merchant_request_id']
        attempt.checkout_request_id = result['checkout_request_id']
        attempt.result_code = result['response_code']
        attempt.result_description = 'Payment prompt accepted by provider.'
        attempt.save(update_fields=['merchant_request_id','checkout_request_id','result_code','result_description','updated_at'])
        purchase.initiation_status = 'submitted'
    except Exception:
        # Ambiguous network errors must not trigger another charge automatically.
        purchase.initiation_status = 'unconfirmed'
        attempt.result_description = 'Provider submission unconfirmed; check phone and reconcile before retrying.'
        attempt.save(update_fields=['result_description','updated_at'])
    purchase.save(update_fields=['initiation_status'])
    return purchase, token


def finalize_purchase(attempt_id):
    # Query confirmation uses the existing tenant-specific Daraja credentials.
    attempt = PaymentAttempt.objects.select_related('payment_configuration').get(pk=attempt_id)
    if attempt.status != 'successful':
        raise ValidationError('Payment is not successful.')
    if attempt.payment_configuration.environment == 'production' and attempt.settlement_status != 'settled':
        result = StkPushService(attempt.payment_configuration).query(checkout_request_id=attempt.checkout_request_id)
        if str(result.get('result_code')) != '0':
            raise ValidationError('Awaiting provider confirmation.')
    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
        purchase = HotspotPurchase.objects.select_for_update().select_related('plan__organization', 'nas__organization').get(attempt=attempt)
        if purchase.voucher_id:
            return purchase.voucher
        if (attempt.status != 'successful' or attempt.service_type != 'hotspot' or attempt.purpose != 'hotspot_purchase'
                or attempt.organization_id != purchase.nas.organization_id or attempt.amount != purchase.price
                or attempt.payment_configuration.organization_id != attempt.organization_id or not attempt.mpesa_receipt_number):
            raise ValidationError('Payment does not match the purchase.')
        receipt = attempt.mpesa_receipt_number
        if HotspotSale.objects.filter(receipt=receipt).exists() or PaymentTransaction.objects.filter(payment_method='mpesa', transaction_id=receipt).exists():
            raise ValidationError('Receipt already recorded.')
        # A paid entitlement is honored even if the operator deactivated the plan after checkout.
        batch = issue_batch_for_paid_purchase(purchase)
        voucher = batch.vouchers.get()
        HotspotSale.objects.create(voucher=voucher, organization=attempt.organization, amount=purchase.price, method='mpesa', receipt=receipt)
        purchase.voucher = voucher
        purchase.save(update_fields=['voucher'])
        attempt.settlement_status, attempt.provisioning_status = 'settled', 'provisioned'
        attempt.save(update_fields=['settlement_status', 'provisioning_status', 'updated_at'])
        AuditService.log(organization=attempt.organization, action='hotspot.payment_settled', resource_type='HotspotPurchase',
                         resource_id=purchase.pk, metadata={'attempt_id': attempt.pk, 'voucher_id': str(voucher.pk)})
        return voucher


def issue_batch_for_paid_purchase(purchase):
    from .models import VoucherBatch, Voucher
    batch = VoucherBatch.objects.create(organization=purchase.nas.organization, plan=purchase.plan, label='M-Pesa purchase')
    code = 'HS' + secrets.token_hex(16).upper()
    Voucher.objects.create(organization=purchase.nas.organization, batch=batch, code=code, code_hash=digest(code), **purchase.entitlement)
    return batch
