import uuid
from django.db import models
from django.utils import timezone
from core.fields import EncryptedTextField


class HotspotPlan(models.Model):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_seconds = models.PositiveIntegerField()
    upload_kbps = models.PositiveIntegerField()
    download_kbps = models.PositiveIntegerField()
    quota_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price', 'id']
        constraints = [models.UniqueConstraint(fields=['organization', 'name'], name='unique_hotspot_plan_name')]


class VoucherBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT)
    plan = models.ForeignKey(HotspotPlan, on_delete=models.PROTECT)
    label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Voucher(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT)
    batch = models.ForeignKey(VoucherBatch, on_delete=models.PROTECT, related_name='vouchers')
    code_hash = models.CharField(max_length=64, unique=True)
    code = EncryptedTextField()
    # Snapshot commercial entitlements: later plan edits never alter issued vouchers.
    plan_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_seconds = models.PositiveIntegerField()
    upload_kbps = models.PositiveIntegerField()
    download_kbps = models.PositiveIntegerField()
    quota_bytes = models.PositiveBigIntegerField(null=True)
    status = models.CharField(max_length=20, default='unused')
    activated_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(null=True)
    redeem_before = models.DateTimeField(null=True)
    bound_mac = models.CharField(max_length=32, blank=True)
    reserved_mac = models.CharField(max_length=32, blank=True)
    reserved_session_id = models.CharField(max_length=253, blank=True)
    reserved_nas = models.ForeignKey('radius.NasDevice', null=True, on_delete=models.PROTECT)
    reservation_until = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'id']


class HotspotSession(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT, related_name='sessions')
    nas = models.ForeignKey('radius.NasDevice', on_delete=models.PROTECT)
    session_id = models.CharField(max_length=253)
    mac = models.CharField(max_length=32)
    ip = models.GenericIPAddressField(null=True)
    started_at = models.DateTimeField(null=True)
    disconnected_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(default=timezone.now)
    stopped_at = models.DateTimeField(null=True)
    upload_bytes = models.PositiveBigIntegerField(default=0)
    download_bytes = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    terminate_cause = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-started_at', '-id']
        constraints = [models.UniqueConstraint(fields=['nas', 'session_id'], name='unique_hotspot_nas_session')]


class HotspotPurchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nas = models.ForeignKey('radius.NasDevice', on_delete=models.PROTECT)
    plan = models.ForeignKey(HotspotPlan, on_delete=models.PROTECT)
    token_hash = models.CharField(max_length=64, unique=True)
    recovery_token = EncryptedTextField(default='')
    request_id = models.UUIDField(default=uuid.uuid4, unique=True)
    phone_hash = models.CharField(max_length=64, default='', db_index=True)
    initiation_status = models.CharField(max_length=20, default='pending')
    attempt = models.OneToOneField('payments.PaymentAttempt', null=True, on_delete=models.PROTECT, related_name='hotspot_purchase')
    voucher = models.OneToOneField(Voucher, null=True, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Frozen entitlement at checkout, regardless of subsequent plan edits.
    entitlement = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class HotspotSale(models.Model):
    voucher = models.OneToOneField(Voucher, on_delete=models.PROTECT, related_name='sale')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10)
    receipt = models.CharField(max_length=100, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
