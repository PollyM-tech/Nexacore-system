from django.db import transaction
from django.utils import timezone

from payments.models import PaymentAttempt

from .stk import (
    StkPushService,
    StkQueryError,
)


class PaymentReconciliationError(Exception):
    """Raised when an STK payment cannot be reconciled."""


class PaymentReconciliationService:
    """
    Reconcile STK attempts whose callback may have been
    delayed or missed.

    Important:
    A successful STK query does not create an accounting
    transaction unless Lintech also has the M-Pesa receipt.
    """

    @staticmethod
    def _map_failure_status(
        result_code,
        result_description,
    ):
        """
        Convert common Daraja failure descriptions into
        Lintech payment statuses.

        Unknown non-zero codes remain failed.
        """

        description = (
            result_description or ""
        ).lower()

        if (
            "cancel" in description
            or result_code == "1032"
        ):
            return "cancelled"

        if (
            "timeout" in description
            or "timed out" in description
            or result_code == "1037"
        ):
            return "timeout"

        return "failed"

    @staticmethod
    @transaction.atomic
    def reconcile_attempt(
        attempt_id,
    ):
        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .get(pk=attempt_id)
        )

        # Already financially complete.
        if (
            attempt.status == "successful"
            and attempt.settlement_status == "settled"
        ):
            attempt.reconciled_at = timezone.now()

            attempt.save(
                update_fields=[
                    "reconciled_at",
                    "updated_at",
                ]
            )

            return {
                "attempt_id": attempt.pk,
                "status": attempt.status,
                "settlement_status": (
                    attempt.settlement_status
                ),
                "action": "already_settled",
            }

        if not attempt.checkout_request_id:
            raise PaymentReconciliationError(
                "Payment attempt has no CheckoutRequestID."
            )

        service = StkPushService(
            attempt.payment_configuration
        )

        try:
            result = service.query(
                checkout_request_id=(
                    attempt.checkout_request_id
                )
            )

        except StkQueryError as exc:
            raise PaymentReconciliationError(
                str(exc)
            ) from exc

        result_code = str(
            result.get(
                "result_code",
                "",
            )
        )

        result_description = str(
            result.get(
                "result_description",
                "",
            )
        )

        attempt.result_code = result_code
        attempt.result_description = (
            result_description
        )

        attempt.reconciled_at = timezone.now()

        # -----------------------------------------------------
        # Safaricom confirms the STK transaction succeeded.
        # -----------------------------------------------------
        if result_code == "0":
            # If the normal callback already supplied the
            # receipt, this attempt can continue through the
            # normal background processing pipeline.
            if attempt.mpesa_receipt_number:
                attempt.status = "successful"

                attempt.save(
                    update_fields=[
                        "result_code",
                        "result_description",
                        "status",
                        "reconciled_at",
                        "updated_at",
                    ]
                )

                return {
                    "attempt_id": attempt.pk,
                    "status": "successful",
                    "settlement_status": (
                        attempt.settlement_status
                    ),
                    "action": (
                        "confirmed_success_with_receipt"
                    ),
                }

            # STK Query confirms success but does not give us
            # a safe accounting receipt to use as Lintech's
            # transaction identifier.
            #
            # Leave status pending so a delayed callback can
            # still supply the receipt and pass through the
            # normal callback processing path.
            attempt.status = "pending"

            attempt.result_description = (
                f"{result_description} "
                "STK query confirms success, but Lintech "
                "is still awaiting the M-Pesa receipt "
                "from the callback."
            ).strip()

            attempt.save(
                update_fields=[
                    "result_code",
                    "result_description",
                    "status",
                    "reconciled_at",
                    "updated_at",
                ]
            )

            return {
                "attempt_id": attempt.pk,
                "status": "pending",
                "settlement_status": (
                    attempt.settlement_status
                ),
                "action": (
                    "success_waiting_for_receipt"
                ),
            }

        # -----------------------------------------------------
        # Safaricom confirms the STK request did not succeed.
        # -----------------------------------------------------
        attempt.status = (
            PaymentReconciliationService
            ._map_failure_status(
                result_code,
                result_description,
            )
        )

        attempt.completed_at = timezone.now()

        attempt.save(
            update_fields=[
                "result_code",
                "result_description",
                "status",
                "reconciled_at",
                "completed_at",
                "updated_at",
            ]
        )

        return {
            "attempt_id": attempt.pk,
            "status": attempt.status,
            "settlement_status": (
                attempt.settlement_status
            ),
            "action": "marked_unsuccessful",
        }