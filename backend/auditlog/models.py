from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit record for sensitive Lintech actions.

    Organization may be null for platform-wide actions,
    such as global scheduler administration.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    actor_role = models.CharField(
        max_length=32,
        blank=True,
        default="",
    )

    action = models.CharField(
        max_length=64,
    )

    resource_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    resource_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    request_method = models.CharField(
        max_length=10,
        blank=True,
        default="",
    )

    request_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "created_at",
                ],
                name="audit_org_created_idx",
            ),
            models.Index(
                fields=[
                    "action",
                    "created_at",
                ],
                name="audit_action_created_idx",
            ),
            models.Index(
                fields=[
                    "resource_type",
                    "resource_id",
                ],
                name="audit_resource_idx",
            ),
        ]

    def __str__(self):
        actor = (
            self.user.get_username()
            if self.user
            else "system"
        )

        return (
            f"{actor}: {self.action} "
            f"{self.resource_type} "
            f"{self.resource_id}"
        )