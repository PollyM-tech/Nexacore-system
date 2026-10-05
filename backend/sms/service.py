import requests

from customers.models import CustomerProfile

from .models import SmsGateway, SmsLog
from .providers import build_spec


TIMEOUT = 20


def normalize_mobile(
    num: str,
) -> str:
    return "".join(
        ch
        for ch in str(
            num or ""
        )
        if ch.isdigit()
        or ch == "+"
    )


def render_message(
    text: str,
    customer: CustomerProfile | None,
) -> str:
    if not customer:
        return text

    package = (
        customer.package.name
        if customer.package_id
        else ""
    )

    balance = float(
        customer.balance or 0
    )

    values = {
        "name": customer.customer_name,
        "customer_id": customer.customer_id,
        "phone": customer.phone_number,
        "package": package,
        "zone": (
            customer.zone.name
            if customer.zone_id
            else ""
        ),
        "balance": f"{balance:.0f}",
        "due": (
            f"{abs(balance):.0f}"
            if balance < 0
            else "0"
        ),
        "billing_day": (
            customer.billing_date.day
            if customer.billing_date
            else ""
        ),
    }

    for key, value in values.items():
        text = text.replace(
            "{" + key + "}",
            str(value),
        )

    return text


def get_default_gateway(
    organization,
) -> SmsGateway | None:
    """
    Return only the current organization's
    active default SMS gateway.
    """

    return (
        SmsGateway.objects
        .filter(
            organization=organization,
            is_default=True,
            is_active=True,
        )
        .first()
        or
        SmsGateway.objects
        .filter(
            organization=organization,
            is_active=True,
        )
        .first()
    )


class SmsService:
    @staticmethod
    def send_one(
        organization,
        mobile,
        message,
        gateway=None,
        customer=None,
        user=None,
    ) -> SmsLog:
        """
        Send one SMS and permanently log it against
        the owning organization.
        """

        if (
            gateway
            and gateway.organization_id
            != organization.id
        ):
            raise ValueError(
                "SMS gateway does not belong "
                "to this organization."
            )

        if (
            customer
            and customer.organization_id
            != organization.id
        ):
            raise ValueError(
                "Customer does not belong "
                "to this organization."
            )

        gateway = (
            gateway
            or get_default_gateway(
                organization
            )
        )

        mobile = normalize_mobile(
            mobile
        )

        status = "failed"
        response = ""

        if not gateway:
            response = (
                "No active SMS gateway "
                "configured."
            )

        else:
            try:
                credentials = dict(
                    gateway.credentials or {}
                )
                if gateway.sender_id:
                    credentials["sender_id"] = (
                        gateway.sender_id
                    )
                spec = build_spec(
                    gateway.provider,
                    credentials,
                    mobile,
                    message,
                )

                request_response = requests.request(
                    spec.method,
                    spec.url,
                    params=(
                        spec.params
                        or None
                    ),
                    data=(
                        spec.data
                        or None
                    ),
                    json=spec.json,
                    headers=(
                        spec.headers
                        or None
                    ),
                    timeout=TIMEOUT,
                )

                response = (
                    request_response.text
                    or ""
                )[:2000]

                status = (
                    "sent"
                    if request_response.ok
                    else "failed"
                )

            except Exception as exc:
                response = str(
                    exc
                )[:2000]

        return SmsLog.objects.create(
            organization=organization,
            customer=customer,
            mobile=mobile,
            message=message,
            provider=(
                gateway.provider
                if gateway
                else ""
            ),
            status=status,
            response=response,
            sent_by=(
                user
                if getattr(
                    user,
                    "is_authenticated",
                    False,
                )
                else None
            ),
        )

    @staticmethod
    def send_bulk(
        organization,
        recipients,
        message_template,
        gateway=None,
        user=None,
    ) -> dict:
        """
        Send an SMS to multiple recipients belonging
        to one organization.
        """

        if (
            gateway
            and gateway.organization_id
            != organization.id
        ):
            raise ValueError(
                "SMS gateway does not belong "
                "to this organization."
            )

        gateway = (
            gateway
            or get_default_gateway(
                organization
            )
        )

        sent = 0
        failed = 0

        for mobile, customer in recipients:
            log = SmsService.send_one(
                organization=organization,
                mobile=mobile,
                message=render_message(
                    message_template,
                    customer,
                ),
                gateway=gateway,
                customer=customer,
                user=user,
            )

            if log.status == "sent":
                sent += 1
            else:
                failed += 1

        return {
            "sent": sent,
            "failed": failed,
            "total": (
                sent + failed
            ),
        }