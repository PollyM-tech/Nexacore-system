import uuid

from django.conf import settings
from django.db import models

from core.fields import EncryptedJSONField, EncryptedTextField


class MetaInfo(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MpesaConfiguration(MetaInfo):
    """
    M-Pesa / Daraja configuration for one Lintech organization.

    This configuration is created and managed by Lintech platform staff.
    It must not be exposed as editable configuration in an ISP dashboard.
    """

    PAYMENT_MODE_CHOICES = [
        ("own_shortcode", "ISP-Owned Shortcode"),
        ("lintech_managed", "Lintech Managed"),
    ]

    SERVICE_SCOPE_CHOICES = [
        ("pppoe", "PPPoE"),
        ("hotspot", "Hotspot"),
        ("both", "PPPoE and Hotspot"),
    ]

    ENVIRONMENT_CHOICES = [
        ("sandbox", "Sandbox"),
        ("production", "Production"),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ("paybill", "PayBill"),
        ("till", "Till / Buy Goods"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="mpesa_configurations",
    )

    payment_mode = models.CharField(
        max_length=30,
        choices=PAYMENT_MODE_CHOICES,
        default="own_shortcode",
    )

    service_scope = models.CharField(
        max_length=20,
        choices=SERVICE_SCOPE_CHOICES,
        default="pppoe",
    )

    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default="sandbox",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default="paybill",
    )

    shortcode = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    consumer_key = EncryptedTextField(
        blank=True,
        default="",
    )

    consumer_secret = EncryptedTextField(
        blank=True,
        default="",
    )

    passkey = EncryptedTextField(
        blank=True,
        default="",
    )

    callback_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    is_active = models.BooleanField(default=True)

    is_default = models.BooleanField(default=False)

    configured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configured_mpesa_integrations",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    def __str__(self):
        return (
            f"{self.organization.name} - "
            f"{self.get_service_scope_display()} - "
            f"{self.shortcode or self.get_payment_mode_display()}"
        )

    class Meta:
        ordering = [
            "organization_id",
            "service_scope",
            "-is_default",
        ]
        verbose_name = "M-Pesa Configuration"
        verbose_name_plural = "M-Pesa Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "service_scope",
                ],
                condition=models.Q(
                    is_active=True,
                    is_default=True,
                ),
                name="unique_active_default_mpesa_config_per_scope",
            ),
        ]


class PaymentAttempt(MetaInfo):
    """
    Outbound STK Push payment intent.

    PaymentAttempt is not Lintech's accounting ledger.

    After successful settlement, the attempt links to the existing
    billing.PaymentTransaction record.
    """

    SERVICE_TYPE_CHOICES = [
        ("pppoe", "PPPoE"),
        ("hotspot", "Hotspot"),
    ]

    PURPOSE_CHOICES = [
        ("pppoe_renewal", "PPPoE Renewal"),
        ("pppoe_plan_change", "PPPoE Plan Change"),
        ("hotspot_purchase", "Hotspot Purchase"),
        ("connection_fee", "Connection Fee"),
        ("invoice_payment", "Invoice Payment"),
        ("account_topup", "Account Top-up"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("timeout", "Timeout"),
    ]

    SETTLEMENT_STATUS_CHOICES = [
        ("unsettled", "Unsettled"),
        ("settling", "Settling"),
        ("settled", "Settled"),
        ("settlement_failed", "Settlement Failed"),
    ]

    PROVISIONING_STATUS_CHOICES = [
        ("not_required", "Not Required"),
        ("pending", "Pending"),
        ("provisioned", "Provisioned"),
        ("failed", "Failed"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="payment_attempts",
    )

    payment_configuration = models.ForeignKey(
        MpesaConfiguration,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )

    customer = models.ForeignKey(
        "customers.CustomerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_payment_attempts",
    )

    monthly_bill = models.ForeignKey(
        "billing.MonthlyBill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_payment_attempts",
    )

    connection_fee = models.ForeignKey(
        "billing.ConnectionFee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_payment_attempts",
    )

    target_package = models.ForeignKey(
        "billing.Package",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_payment_attempts",
    )

    payment_transaction = models.OneToOneField(
        "billing.PaymentTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_attempt",
    )

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
    )

    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES,
    )

    phone_number = models.CharField(
        max_length=20,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    account_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    merchant_request_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    checkout_request_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
    )

    mpesa_receipt_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    settlement_status = models.CharField(
        max_length=30,
        choices=SETTLEMENT_STATUS_CHOICES,
        default="unsettled",
    )

    provisioning_status = models.CharField(
        max_length=20,
        choices=PROVISIONING_STATUS_CHOICES,
        default="not_required",
    )

    result_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    result_description = models.TextField(
        blank=True,
        default="",
    )

    transaction_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    callback_payload = EncryptedJSONField(
        default=dict,
        blank=True,
    )

    reconciled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"STK #{self.pk} - "
            f"{self.organization.name} - "
            f"{self.amount} - "
            f"{self.status}"
        )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "M-Pesa Payment Attempt"
        verbose_name_plural = "M-Pesa Payment Attempts"
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "status",
                    "created_at",
                ],
                name="mpesa_attempt_org_status_idx",
            ),
            models.Index(
                fields=[
                    "settlement_status",
                    "created_at",
                ],
                name="mpesa_attempt_settle_idx",
            ),
            models.Index(
                fields=[
                    "provisioning_status",
                    "created_at",
                ],
                name="mpesa_attempt_prov_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "payment_configuration",
                    "mpesa_receipt_number",
                ],
                condition=models.Q(
                    mpesa_receipt_number__isnull=False,
                ),
                name="unique_mpesa_receipt_per_config",
            ),
        ]


class C2BTransaction(MetaInfo):
    """
    Inbound manual PayBill/Till transaction.

    A C2B payment may arrive without any prior PaymentAttempt.
    """

    ALLOCATION_STATUS_CHOICES = [
        ("unallocated", "Unallocated"),
        ("matched", "Matched"),
        ("manually_allocated", "Manually Allocated"),
        ("rejected", "Rejected"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="c2b_transactions",
    )

    payment_configuration = models.ForeignKey(
        MpesaConfiguration,
        on_delete=models.PROTECT,
        related_name="c2b_transactions",
    )

    customer = models.ForeignKey(
        "customers.CustomerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="c2b_transactions",
    )

    payment_transaction = models.OneToOneField(
        "billing.PaymentTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="c2b_transaction",
    )

    trans_id = models.CharField(
        max_length=50,
    )

    bill_ref_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    business_shortcode = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    allocation_status = models.CharField(
        max_length=30,
        choices=ALLOCATION_STATUS_CHOICES,
        default="unallocated",
    )

    raw_payload = EncryptedJSONField(
        default=dict,
        blank=True,
    )

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    allocated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"C2B {self.trans_id} - "
            f"{self.organization.name} - "
            f"{self.amount}"
        )

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "M-Pesa C2B Transaction"
        verbose_name_plural = "M-Pesa C2B Transactions"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "payment_configuration",
                    "trans_id",
                ],
                name="unique_c2b_trans_per_config",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "allocation_status",
                    "received_at",
                ],
                name="c2b_org_alloc_status_idx",
            ),
        ]