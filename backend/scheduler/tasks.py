import calendar
from datetime import timedelta

from django.utils import timezone


def monthly_bill_job():
    """
    Automatically generate monthly bills for every active organization.
    """
    from billing.services import BillingService
    from organizations.models import Organization

    organizations = Organization.objects.filter(
        is_active=True,
        status="active",
    )

    for organization in organizations:
        BillingService.create_monthly_bills(
            organization
        )


def bill_due_disconnect_job():
    """
    Disconnect overdue customers and best-effort sync the status
    to the correct organization's MikroTik router.
    """
    from billing.models import (
        ConnectionFee,
        MonthlyBill,
    )
    from customers.models import CustomerProfile
    from customers.service import CustomerService

    today = timezone.localdate()

    active_customers = (
        CustomerProfile.objects
        .filter(
            organization__is_active=True,
            organization__status="active",
            customer_status="active",
            billing_date__isnull=False,
        )
        .select_related(
            "organization"
        )
    )

    for customer in active_customers:
        due_date = (
            customer.billing_date
            + timedelta(
                days=customer.extended_billing_days
            )
        )

        if today <= due_date:
            continue

        has_unpaid_monthly = (
            MonthlyBill.objects
            .filter(
                customer=customer,
                payment_status__in=[
                    "unpaid",
                    "partial",
                ],
            )
            .exists()
        )

        has_unpaid_connection = (
            ConnectionFee.objects
            .filter(
                customer=customer,
                payment_status__in=[
                    "unpaid",
                    "partial",
                ],
            )
            .exists()
        )

        if not (
            has_unpaid_monthly
            or has_unpaid_connection
        ):
            continue

        try:
            CustomerService.update_customer_status(
                customer.organization,
                customer.customer_id,
                "disconnected",
            )
        except Exception:
            # One failed router/customer must not stop
            # processing every other ISP/customer.
            continue


def billing_date_update_job():
    """
    Move customers' billing dates into the current billing cycle
    and clear temporary extended billing days.
    """
    from customers.models import CustomerProfile

    today = timezone.localdate()

    customers = CustomerProfile.objects.filter(
        organization__is_active=True,
        billing_date__isnull=False,
    )

    for customer in customers:
        billing_date = customer.billing_date

        is_previous_cycle = (
            billing_date.year < today.year
            or (
                billing_date.year == today.year
                and billing_date.month < today.month
            )
        )

        if not is_previous_cycle:
            continue

        last_day = calendar.monthrange(
            today.year,
            today.month,
        )[1]

        target_day = min(
            billing_date.day,
            last_day,
        )

        customer.billing_date = billing_date.replace(
            year=today.year,
            month=today.month,
            day=target_day,
        )

        customer.extended_billing_days = 0

        customer.save(
            update_fields=[
                "billing_date",
                "extended_billing_days",
                "updated_at",
            ]
        )


def payment_provisioning_retry_job():
    """
    Retry network provisioning for settled M-Pesa payments
    whose previous provisioning attempt failed.

    Retrying a failed attempt must not extend the customer's
    billing date again.
    """
    from payments.models import PaymentAttempt
    from payments.services import (
        PaymentProvisioningService,
    )

    attempts = (
        PaymentAttempt.objects
        .filter(
            status="successful",
            settlement_status="settled",
            provisioning_status="failed",
            organization__is_active=True,
            organization__status="active",
        )
        .order_by("created_at")
    )

    processed = 0
    provisioned = 0
    failed = 0

    for attempt in attempts.iterator():
        processed += 1

        try:
            PaymentProvisioningService.provision_stk_attempt(
                attempt.pk
            )
            provisioned += 1

        except Exception:
            # Router outages or individual provisioning failures
            # must not stop retries for other customers.
            failed += 1
            continue

    return {
        "status": "ok",
        "processed": processed,
        "provisioned": provisioned,
        "failed": failed,
    }