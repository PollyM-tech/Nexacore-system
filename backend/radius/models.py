import uuid
from django.db import models
from django.utils import timezone
from core.fields import EncryptedTextField


class RadiusCheck(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default=":=")
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = "radcheck"


class RadiusReply(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default="=")
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = "radreply"


class RadAcct(models.Model):
    radacctid = models.BigAutoField(
        primary_key=True,
    )

    acctsessionid = models.TextField()
    acctuniqueid = models.TextField()

    username = models.TextField(
        null=True,
        blank=True,
    )

    realm = models.TextField(
        null=True,
        blank=True,
    )

    nasipaddress = models.GenericIPAddressField()

    nasportid = models.TextField(
        null=True,
        blank=True,
    )

    nasporttype = models.TextField(
        null=True,
        blank=True,
    )

    acctstarttime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctupdatetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctstoptime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctinterval = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctsessiontime = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctauthentic = models.TextField(
        null=True,
        blank=True,
    )

    connectinfo_start = models.TextField(
        null=True,
        blank=True,
    )

    connectinfo_stop = models.TextField(
        null=True,
        blank=True,
    )

    acctinputoctets = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctoutputoctets = models.BigIntegerField(
        null=True,
        blank=True,
    )

    calledstationid = models.TextField(
        null=True,
        blank=True,
    )

    callingstationid = models.TextField(
        null=True,
        blank=True,
    )

    acctterminatecause = models.TextField(
        null=True,
        blank=True,
    )

    servicetype = models.TextField(
        null=True,
        blank=True,
    )

    framedprotocol = models.TextField(
        null=True,
        blank=True,
    )

    framedipaddress = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedipv6address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedipv6prefix = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedinterfaceid = models.TextField(
        null=True,
        blank=True,
    )

    delegatedipv6prefix = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class_value = models.TextField(
        db_column="class",
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "radacct"
        ordering = [
            "-acctstarttime",
        ]

    def __str__(self):
        return (
            f"{self.username or 'unknown'} "
            f"- {self.acctsessionid}"
        )

    @property
    def is_active(self):
        return (
            self.acctstarttime is not None
            and self.acctstoptime is None
        )

    @property
    def total_bytes(self):
        return (
            (self.acctinputoctets or 0)
            + (self.acctoutputoctets or 0)
        )

class NasDevice(models.Model):
    """RADIUS source identity, independent of RouterOS administrative access."""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.PROTECT, related_name='nas_devices')
    router = models.OneToOneField('mikrotik.MikrotikRouter', null=True, blank=True, on_delete=models.PROTECT, related_name='radius_nas')
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100)
    source_ip = models.GenericIPAddressField(protocol='IPv4', unique=True)
    identifier = models.CharField(max_length=64, blank=True)
    shared_secret = EncryptedTextField()
    disconnect_port = models.PositiveIntegerField(default=3799)
    is_active = models.BooleanField(default=True)
    hotspot_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']


class DisconnectRequest(models.Model):
    nas = models.ForeignKey(NasDevice, on_delete=models.PROTECT, related_name='disconnect_requests')
    username = EncryptedTextField()
    username_hash = models.CharField(max_length=64)
    session_id = models.CharField(max_length=253)
    caller_id = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=40)
    status = models.CharField(max_length=20, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    claimed_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=80, blank=True)
    acknowledged_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['nas', 'username_hash', 'session_id', 'reason'], name='unique_disconnect_reason_session')]
        indexes = [models.Index(fields=['status', 'next_attempt_at'])]


class DisconnectAttempt(models.Model):
    request = models.ForeignKey(DisconnectRequest, on_delete=models.CASCADE, related_name='events')
    number = models.PositiveIntegerField()
    result = models.CharField(max_length=20)
    error_cause = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
