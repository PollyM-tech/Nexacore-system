import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimeStampedModel):
    ORGANIZATION_TYPE_CHOICES = [
        ("hotspot", "Hotspot ISP"),
        ("pppoe", "PPPoE ISP"),
        ("hybrid", "Hotspot + PPPoE"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("inactive", "Inactive"),
    ]

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)

    organization_type = models.CharField(
        max_length=20,
        choices=ORGANIZATION_TYPE_CHOICES,
        default="hybrid",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    country = models.CharField(
        max_length=2,
        default="KE",
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    timezone = models.CharField(
        max_length=50,
        default="Africa/Nairobi",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class OrganizationMembership(TimeStampedModel):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("technician", "Technician"),
        ("billing", "Billing"),
        ("support", "Support"),
        ("viewer", "Viewer"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="viewer",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.organization} - {self.role}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_user_membership",
            )
        ]