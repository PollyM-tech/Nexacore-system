from django.db import IntegrityError, transaction

from billing.models import PaymentTransaction
from billing.services import BillingService
from payments.models import PaymentAttempt


class PaymentSettlementError(Exception):
    """Raised when a confirmed M-Pesa payment cannot be settled."""


class PaymentSettlementService:
    @staticmethod
    @transaction.atomic
    def settle_stk_attempt(attempt_id):
        """
        Settle one successful STK payment into Lintech's billing ledger.

        The PaymentAttempt row is locked so two workers cannot settle
        the same M-Pesa payment at the same time.

        BillingService separately locks the customer while allocating
        the payment to outstanding invoices.
        """

        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .get(pk=attempt_id)
        )

        if attempt.status != "successful":
            raise PaymentSettlementError(
                "Only successful M-Pesa attempts can be settled."
            )

        # Idempotent retry: already settled means there is nothing
        # further to do.
        if attempt.settlement_status == "settled":
            return attempt.payment_transaction

        if not attempt.customer_id:
            raise PaymentSettlementError(
                "Payment attempt has no customer."
            )

        if not attempt.mpesa_receipt_number:
            raise PaymentSettlementError(
                "Successful M-Pesa attempt has no receipt number."
            )

        existing = (
            PaymentTransaction.objects
            .filter(
                payment_method="mpesa",
                transaction_id=attempt.mpesa_receipt_number,
            )
            .first()
        )

        if existing:
            attempt.payment_transaction = existing
            attempt.settlement_status = "settled"

            attempt.save(
                update_fields=[
                    "payment_transaction",
                    "settlement_status",
                    "updated_at",
                ]
            )

            return existing

        attempt.settlement_status = "settling"

        attempt.save(
            update_fields=[
                "settlement_status",
                "updated_at",
            ]
        )

        try:
            payment_transaction = (
                BillingService.add_payment_transaction(
                    organization=attempt.organization,
                    customer_id=attempt.customer.customer_id,
                    amount=attempt.amount,
                    payment_method="mpesa",
                    transaction_id=attempt.mpesa_receipt_number,
                    received_by=None,
                    notes=(
                        f"M-Pesa STK payment. "
                        f"Attempt #{attempt.pk}. "
                        f"Purpose: {attempt.purpose}."
                    ),
                )
            )

        except IntegrityError as exc:
            raise PaymentSettlementError(
                "This M-Pesa receipt has already been recorded."
            ) from exc

        attempt.payment_transaction = payment_transaction
        attempt.settlement_status = "settled"

        attempt.save(
            update_fields=[
                "payment_transaction",
                "settlement_status",
                "updated_at",
            ]
        )

        return payment_transaction