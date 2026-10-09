from dateutil.relativedelta import relativedelta

from django.db import transaction
from django.utils import timezone

from customers.models import CustomerProfile
from customers.service import CustomerService
from payments.models import PaymentAttempt


class ProvisioningError(Exception):
    """Raised when a settled payment cannot be provisioned."""


class PaymentProvisioningService:
    @staticmethod
    def provision_stk_attempt(attempt_id):
        """
        Apply the paid renewal entitlement once, then try to activate
        the customer's PPPoE service.

        A router failure must not roll back the paid renewal.
        Retrying a failed provisioning attempt must not extend the
        customer's billing date a second time.
        """

        # ---------------------------------------------------------
        # Stage 1: validate payment and permanently apply renewal.
        # ---------------------------------------------------------
        with transaction.atomic():
            attempt = (
                PaymentAttempt.objects
                .select_for_update()
                .get(pk=attempt_id)
            )

            if attempt.status != "successful":
                raise ProvisioningError(
                    "Only successful payments can be provisioned."
                )

            if attempt.settlement_status != "settled":
                raise ProvisioningError(
                    "Payment must be settled before provisioning."
                )

            if attempt.provisioning_status == "provisioned":
                return CustomerProfile.objects.get(
                    pk=attempt.customer_id
                )

            if attempt.service_type != "pppoe":
                raise ProvisioningError(
                    "This provisioning service currently handles PPPoE only."
                )

            if attempt.purpose not in (
                "pppoe_renewal",
                "pppoe_plan_change",
            ):
                raise ProvisioningError(
                    "Payment purpose does not require PPPoE provisioning."
                )

            if not attempt.customer_id:
                raise ProvisioningError(
                    "Payment attempt has no customer."
                )

            if not attempt.monthly_bill_id:
                raise ProvisioningError(
                    "PPPoE renewal payment is not linked to a monthly bill."
                )

            bill = attempt.monthly_bill

            if bill.payment_status != "paid":
                raise ProvisioningError(
                    "Monthly bill is not fully paid."
                )

            customer = ( CustomerProfile.objects
                        .select_for_update()
                        .get(pk=attempt.customer_id)
                        )

            if not customer.package_id:
                raise ProvisioningError(
                    "Customer has no package assigned."
                )

            # Apply the subscription extension only once.
            #
            # not_required means this payment has never had its
            # renewal entitlement applied.
            if attempt.provisioning_status == "not_required":
                today = timezone.localdate()

                if (
                    customer.billing_date
                    and customer.billing_date > today
                ):
                    base_date = customer.billing_date
                else:
                    base_date = today

                package_type = customer.package.package_type

                if package_type == "monthly":
                    new_billing_date = (
                        base_date
                        + relativedelta(months=1)
                    )

                elif package_type == "quarterly":
                    new_billing_date = (
                        base_date
                        + relativedelta(months=3)
                    )

                elif package_type == "yearly":
                    new_billing_date = (
                        base_date
                        + relativedelta(years=1)
                    )

                else:
                    raise ProvisioningError(
                        f"Unsupported package type: {package_type}"
                    )

                customer.billing_date = new_billing_date
                customer.save(
                    update_fields=[
                        "billing_date",
                        "updated_at",
                    ]
                )

            attempt.provisioning_status = "pending"
            attempt.save(
                update_fields=[
                    "provisioning_status",
                    "updated_at",
                ]
            )

            original_status = customer.customer_status

        # At this point the renewal date and pending state are committed.
        # A MikroTik failure below cannot undo them.

        # ---------------------------------------------------------
        # Stage 2: attempt network activation.
        # ---------------------------------------------------------
        try:
            customer, warning = CustomerService.update_customer_status(
                organization=attempt.organization,
                customer_id=customer.customer_id,
                status_value="active",
            )

            if warning:
                # CustomerService saves locally before router sync.
                # Restore the previous local state because the network
                # activation did not actually complete.
                customer.customer_status = original_status
                customer.save(
                    update_fields=[
                        "customer_status",
                        "updated_at",
                    ]
                )

                PaymentAttempt.objects.filter(
                    pk=attempt.pk
                ).update(
                    provisioning_status="failed",
                )

                raise ProvisioningError(warning)

        except ProvisioningError:
            raise

        except Exception as exc:
            CustomerProfile.objects.filter(
                pk=customer.pk
            ).update(
                customer_status=original_status,
            )

            PaymentAttempt.objects.filter(
                pk=attempt.pk
            ).update(
                provisioning_status="failed",
            )

            raise ProvisioningError(
                f"Customer activation failed: {exc}"
            ) from exc

        # ---------------------------------------------------------
        # Stage 3: network activation completed.
        # ---------------------------------------------------------
        PaymentAttempt.objects.filter(
            pk=attempt.pk
        ).update(
            provisioning_status="provisioned",
        )

        customer.refresh_from_db()

        return customer