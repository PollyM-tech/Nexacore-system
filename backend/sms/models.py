from django.contrib.auth.models import User
from django.db import models

from core.fields import EncryptedJSONField
from customers.models import (
    CustomerProfile,
    MetaInfo,
)


class SmsGateway(MetaInfo):
    """
    SMS provider configuration owned by one
    ISP organization.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="sms_gateways",
    )

    provider = models.CharField(
        max_length=50,
    )

    label = models.CharField(
        max_length=100,
    )

    sender_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    credentials = EncryptedJSONField(
        default=dict,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = [
            "-is_default",
            "label",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "label",
                ],
                name=(
                    "unique_sms_gateway_label_"
                    "per_organization"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.label} "
            f"({self.provider})"
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        super().save(
            *args,
            **kwargs,
        )

        if (
            self.is_default
            and self.organization_id
        ):
            (
                SmsGateway.objects
                .filter(
                    organization_id=(
                        self.organization_id
                    ),
                    is_default=True,
                )
                .exclude(
                    pk=self.pk
                )
                .update(
                    is_default=False
                )
            )


class SmsTemplate(MetaInfo):
    CATEGORY_CHOICES = [
        (
            "bill",
            "Bill / Invoice",
        ),
        (
            "payment",
            "Payment received",
        ),
        (
            "reminder",
            "Due reminder",
        ),
        (
            "welcome",
            "Welcome",
        ),
        (
            "notice",
            "General notice",
        ),
        (
            "custom",
            "Custom",
        ),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="sms_templates",
    )

    name = models.CharField(
        max_length=120,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="custom",
    )

    body = models.TextField()

    class Meta:
        ordering = [
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "name",
                ],
                name=(
                    "unique_sms_template_name_"
                    "per_organization"
                ),
            )
        ]

    def __str__(self):
        return self.name


class SmsLog(MetaInfo):
    STATUS_CHOICES = [
        (
            "sent",
            "Sent",
        ),
        (
            "failed",
            "Failed",
        ),
        (
            "queued",
            "Queued",
        ),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="sms_logs",
    )

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_logs",
    )

    mobile = models.CharField(
        max_length=20,
    )

    message = models.TextField()

    provider = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="sent",
    )

    response = models.TextField(
        blank=True,
        default="",
    )

    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_sms",
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "created_at",
                ],
                name=(
                    "smslog_org_created_idx"
                ),
            ),
            models.Index(
                fields=[
                    "organization",
                    "status",
                ],
                name=(
                    "smslog_org_status_idx"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.mobile} - "
            f"{self.status}"
        )