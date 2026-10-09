from decimal import Decimal

from django.db import transaction

from payments.models import PaymentAttempt

from .stk import StkPushError, StkPushService


class PaymentAttemptService:
    """
    Creates and initiates STK payment attempts.

    A PaymentAttempt always exists before Lintech sends the STK request.
    """

    @staticmethod
    @transaction.atomic
    def create_and_initiate(
        *,
        organization,
        payment_configuration,
        phone_number,
        amount,
        account_reference,
        service_type,
        purpose,
        callback_url,
        customer=None,
        monthly_bill=None,
        connection_fee=None,
        target_package=None,
    ):
        amount = Decimal(str(amount))

        if amount <= 0:
            raise StkPushError(
                "Payment amount must be greater than zero."
            )

        if payment_configuration.organization_id != organization.id:
            raise StkPushError(
                "Payment configuration does not belong to this organization."
            )

        if customer and customer.organization_id != organization.id:
            raise StkPushError(
                "Customer does not belong to this organization."
            )

        if target_package and target_package.organization_id != organization.id:
            raise StkPushError(
                "Package does not belong to this organization."
            )

        attempt = PaymentAttempt.objects.create(
            organization=organization,
            payment_configuration=payment_configuration,
            customer=customer,
            monthly_bill=monthly_bill,
            connection_fee=connection_fee,
            target_package=target_package,
            service_type=service_type,
            purpose=purpose,
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            status="pending",
            settlement_status="unsettled",
            provisioning_status="not_required",
        )

        service = StkPushService(
            payment_configuration
        )

        try:
            result = service.initiate(
                phone_number=phone_number,
                amount=amount,
                account_reference=account_reference,
                callback_url=callback_url,
            )

        except Exception as exc:
            attempt.status = "failed"
            attempt.result_description = str(exc)

            attempt.save(
                update_fields=[
                    "status",
                    "result_description",
                    "updated_at",
                ]
            )

            raise

        attempt.merchant_request_id = (
            result["merchant_request_id"]
        )

        attempt.checkout_request_id = (
            result["checkout_request_id"]
        )

        attempt.result_code = (
            result["response_code"]
        )

        attempt.result_description = (
            result["response_description"]
        )

        attempt.save(
            update_fields=[
                "merchant_request_id",
                "checkout_request_id",
                "result_code",
                "result_description",
                "updated_at",
            ]
        )

        return attempt