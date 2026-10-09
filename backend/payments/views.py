from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django_q.tasks import async_task

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MpesaConfiguration,
    PaymentAttempt,
)


def _metadata_to_dict(items):
    """
    Convert Daraja CallbackMetadata Item list into a normal dictionary.
    """

    result = {}

    if not isinstance(items, list):
        return result

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("Name")

        if not name:
            continue

        result[name] = item.get("Value")

    return result


def _accepted_response():
    """
    Safaricom callback acknowledgement.
    """

    return Response(
        {
            "ResultCode": 0,
            "ResultDesc": "Accepted",
        },
        status=status.HTTP_200_OK,
    )


def _queue_successful_payment_processing(attempt_id):
    """
    Queue settlement and provisioning only after the
    callback database transaction has committed.
    """

    transaction.on_commit(
        lambda: async_task(
            "payments.tasks.process_successful_stk_payment",
            attempt_id,
        )
    )


class StkCallbackView(APIView):
    """
    Public Safaricom STK callback endpoint.

    The callback URL contains a random configuration token.
    The payment is also matched using CheckoutRequestID.

    Successful callbacks are saved first, then settlement
    and provisioning run asynchronously through django-q2.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(
        self,
        request,
        callback_token,
    ):
        configuration = (
            MpesaConfiguration.objects
            .filter(
                callback_token=callback_token,
                is_active=True,
            )
            .first()
        )

        if not configuration:
            return _accepted_response()

        body = request.data.get(
            "Body",
            {},
        )

        if not isinstance(body, dict):
            return _accepted_response()

        callback = body.get(
            "stkCallback",
            {},
        )

        if not isinstance(callback, dict):
            return _accepted_response()

        checkout_request_id = callback.get(
            "CheckoutRequestID"
        )

        merchant_request_id = callback.get(
            "MerchantRequestID"
        )

        if not checkout_request_id:
            return _accepted_response()

        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .filter(
                payment_configuration=configuration,
                checkout_request_id=checkout_request_id,
            )
            .first()
        )

        if not attempt:
            return _accepted_response()

        # ---------------------------------------------------------
        # Handle repeated callbacks safely.
        # ---------------------------------------------------------

        if attempt.status == "successful":
            if attempt.settlement_status == "settled":
                return _accepted_response()

            # Payment succeeded previously but settlement did not
            # finish. Requeue the background processor safely.
            attempt_id = attempt.pk

            _queue_successful_payment_processing(
                attempt_id
            )

            return _accepted_response()

        # ---------------------------------------------------------
        # Read Daraja result.
        # ---------------------------------------------------------

        result_code = str(
            callback.get(
                "ResultCode",
                "",
            )
        )

        result_description = str(
            callback.get(
                "ResultDesc",
                "",
            )
        )

        attempt.callback_payload = request.data
        attempt.result_code = result_code
        attempt.result_description = (
            result_description
        )

        if (
            merchant_request_id
            and not attempt.merchant_request_id
        ):
            attempt.merchant_request_id = (
                merchant_request_id
            )

        # ---------------------------------------------------------
        # Failed/cancelled/timeout STK request.
        # ---------------------------------------------------------

        if result_code != "0":
            attempt.status = "failed"
            attempt.completed_at = (
                timezone.now()
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

            return _accepted_response()

        # ---------------------------------------------------------
        # Successful STK callback metadata.
        # ---------------------------------------------------------

        callback_metadata = callback.get(
            "CallbackMetadata",
            {},
        )

        metadata = _metadata_to_dict(
            callback_metadata.get(
                "Item",
                [],
            )
            if isinstance(
                callback_metadata,
                dict,
            )
            else []
        )

        receipt = metadata.get(
            "MpesaReceiptNumber"
        )

        callback_amount = metadata.get(
            "Amount"
        )

        if (
            not receipt
            or callback_amount is None
        ):
            attempt.status = "failed"

            attempt.result_description = (
                "Successful callback was missing "
                "required payment metadata."
            )

            attempt.completed_at = (
                timezone.now()
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

            return _accepted_response()

        # ---------------------------------------------------------
        # Validate amount.
        # ---------------------------------------------------------

        try:
            callback_amount = Decimal(
                str(callback_amount)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            attempt.status = "failed"

            attempt.result_description = (
                "Daraja callback contained "
                "an invalid amount."
            )

            attempt.completed_at = (
                timezone.now()
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

            return _accepted_response()

        if callback_amount != attempt.amount:
            attempt.status = "failed"

            attempt.result_description = (
                "Daraja callback amount did not "
                "match the expected payment amount."
            )

            attempt.completed_at = (
                timezone.now()
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

            return _accepted_response()

        # ---------------------------------------------------------
        # Payment confirmed by Safaricom.
        # ---------------------------------------------------------

        attempt.mpesa_receipt_number = str(
            receipt
        )

        attempt.status = "successful"

        # Accounting settlement runs asynchronously after
        # this callback transaction commits.
        attempt.settlement_status = (
            "unsettled"
        )

        attempt.completed_at = (
            timezone.now()
        )

        attempt.save(
            update_fields=[
                "callback_payload",
                "result_code",
                "result_description",
                "merchant_request_id",
                "mpesa_receipt_number",
                "status",
                "settlement_status",
                "completed_at",
                "updated_at",
            ]
        )

        attempt_id = attempt.pk

        # Only queue after the successful callback data
        # has committed to PostgreSQL.
        _queue_successful_payment_processing(
            attempt_id
        )

        return _accepted_response()