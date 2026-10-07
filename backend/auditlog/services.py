from copy import deepcopy

from organizations.models import (
    OrganizationMembership,
)

from .models import AuditLog


SENSITIVE_KEYS = {
    "password",
    "pppoe_pass",
    "telnet_password",
    "api_key",
    "apikey",
    "api-key",
    "credentials",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
}


def _redact(value):
    """
    Recursively remove sensitive values before
    storing request metadata in the audit table.
    """

    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            normalized_key = (
                str(key)
                .strip()
                .lower()
            )

            if normalized_key in SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact(item)

        return result

    if isinstance(value, list):
        return [
            _redact(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _redact(item)
            for item in value
        ]

    return value


def _get_client_ip(request):
    if request is None:
        return None

    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded:
        return (
            forwarded
            .split(",")[0]
            .strip()
        )

    return request.META.get(
        "REMOTE_ADDR"
    )


def _get_actor_role(
    user,
    organization,
):
    if (
        not user
        or not user.is_authenticated
    ):
        return ""

    if user.is_superuser:
        return "platform_admin"

    if organization is None:
        return ""

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
        )
        .values_list(
            "role",
            flat=True,
        )
        .first()
    )

    return membership or ""


class AuditService:
    @staticmethod
    def log(
        *,
        action,
        organization=None,
        user=None,
        request=None,
        resource_type="",
        resource_id="",
        description="",
        metadata=None,
    ):
        """
        Write an audit event.

        Audit logging should never store passwords,
        provider keys, tokens, or similar secrets.
        """

        clean_metadata = _redact(
            deepcopy(
                metadata or {}
            )
        )

        request_method = ""
        request_path = ""
        user_agent = ""
        ip_address = None

        if request is not None:
            request_method = (
                request.method or ""
            )

            request_path = (
                request.path or ""
            )

            user_agent = (
                request.META.get(
                    "HTTP_USER_AGENT",
                    "",
                )
            )

            ip_address = _get_client_ip(
                request
            )

            if user is None:
                request_user = getattr(
                    request,
                    "user",
                    None,
                )

                if (
                    request_user
                    and request_user.is_authenticated
                ):
                    user = request_user

        actor_role = _get_actor_role(
            user,
            organization,
        )

        return AuditLog.objects.create(
            organization=organization,
            user=user,
            actor_role=actor_role,
            action=str(action),
            resource_type=(
                str(resource_type)
                if resource_type
                else ""
            ),
            resource_id=(
                str(resource_id)
                if resource_id is not None
                else ""
            ),
            description=description or "",
            request_method=request_method,
            request_path=request_path,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=clean_metadata,
        )