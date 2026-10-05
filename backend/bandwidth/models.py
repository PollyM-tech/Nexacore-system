from django.db import models

from customers.models import CustomerProfile
from mikrotik.models import MikrotikRouter


class BandwidthSample(models.Model):
    """
    A point-in-time snapshot of a PPPoE session's cumulative
    traffic counters.

    Organization ownership is stored directly so historical
    records remain associated with the ISP even if the customer
    or router is later deleted.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="bandwidth_samples",
    )

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bandwidth_samples",
    )

    router = models.ForeignKey(
        MikrotikRouter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bandwidth_samples",
    )

    pppoe_id = models.CharField(
        max_length=255,
        db_index=True,
    )

    customer_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    upload_bytes = models.BigIntegerField(
        default=0,
        help_text="Bytes received from the customer (RX)",
    )

    download_bytes = models.BigIntegerField(
        default=0,
        help_text="Bytes sent to the customer (TX)",
    )

    uptime = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return (
            f"{self.pppoe_id} @ "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )

    class Meta:
        ordering = ["-created_at"]

        verbose_name = "Bandwidth Sample"
        verbose_name_plural = "Bandwidth Samples"

        indexes = [
            models.Index(
                fields=["organization", "created_at"],
                name="bandwidth_org_created_idx",
            ),
            models.Index(
                fields=["organization", "pppoe_id"],
                name="bandwidth_org_pppoe_idx",
            ),
        ]