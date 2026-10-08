from django.db import models

from core.fields import EncryptedTextField
from customers.models import CustomerProfile


class MetaInfo(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


class MikrotikRouter(MetaInfo):
    ROUTER_STATUS_CHOICES = [
        (
            "connected",
            "Connected",
        ),
        (
            "disconnected",
            "Disconnected",
        ),
        (
            "error",
            "Connection Error",
        ),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="mikrotik_routers",
    )

    name = models.CharField(
        max_length=100,
        help_text=(
            "Router name for identification"
        ),
    )

    host = models.CharField(
        max_length=255,
        help_text=(
            "Router IP address or hostname"
        ),
    )

    port = models.IntegerField(
        default=8728,
        help_text=(
            "API port (default: 8728)"
        ),
    )

    username = models.CharField(
        max_length=100,
        help_text=(
            "Router API username"
        ),
    )

    password = EncryptedTextField(
        help_text=(
            "Router API password"
        ),
    )

    use_ssl = models.BooleanField(
        default=False,
        help_text=(
            "Use SSL for connection"
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=ROUTER_STATUS_CHOICES,
        default="disconnected",
    )

    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Last connection check time"
        ),
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.host}:{self.port}"
        )

    class Meta:
        verbose_name = (
            "MikroTik Router"
        )

        verbose_name_plural = (
            "MikroTik Routers"
        )

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
                    "unique_router_name_"
                    "per_organization"
                ),
            ),
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "host",
                    "port",
                ],
                name=(
                    "unique_router_endpoint_"
                    "per_organization"
                ),
            ),
        ]


class RouterInfo(MetaInfo):
    pppoe_name = models.CharField(
        max_length=255,
    )

    pppoe_pass = EncryptedTextField()

    profile_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    remote_ip = (
        models.GenericIPAddressField(
            null=True,
            blank=True,
        )
    )

    customer = models.OneToOneField(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="router_info",
    )

    router = models.ForeignKey(
        MikrotikRouter,
        on_delete=models.CASCADE,
        related_name="customer_routers",
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.pppoe_name} - "
            f"{self.customer.customer_id}"
        )

    class Meta:
        verbose_name = (
            "Customer Router Info"
        )

        verbose_name_plural = (
            "Customer Router Infos"
        )