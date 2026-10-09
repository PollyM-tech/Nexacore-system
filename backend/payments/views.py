from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

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


class StkCallbackView(APIView):
    """
    Public Safaricom STK callback endpoint.

    Authentication is performed using the random callback token embedded
    in the URL plus matching against a known CheckoutRequestID.

    Repeated callbacks are acknowledged safely.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, callback_token):
        configuration = (
            MpesaConfiguration.objects
            .filter(
                callback_token=callback_token,
                is_active=True,
            )
            .first()
        )

        if not configuration:
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        body = request.data.get("Body", {})

        if not isinstance(body, dict):
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        callback = body.get("stkCallback", {})

        if not isinstance(callback, dict):
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        checkout_request_id = callback.get(
            "CheckoutRequestID"
        )

        merchant_request_id = callback.get(
            "MerchantRequestID"
        )

        if not checkout_request_id:
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

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
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        # Callback already fully processed.
        if attempt.status == "successful":
            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        result_code = str(
            callback.get("ResultCode", "")
        )

        result_description = str(
            callback.get("ResultDesc", "")
        )

        attempt.callback_payload = request.data
        attempt.result_code = result_code
        attempt.result_description = result_description

        if (
            merchant_request_id
            and not attempt.merchant_request_id
        ):
            attempt.merchant_request_id = (
                merchant_request_id
            )

        if result_code != "0":
            attempt.status = "failed"
            attempt.completed_at = timezone.now()

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

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        callback_metadata = callback.get(
            "CallbackMetadata",
            {},
        )

        metadata = _metadata_to_dict(
            callback_metadata.get("Item", [])
            if isinstance(callback_metadata, dict)
            else []
        )

        receipt = metadata.get(
            "MpesaReceiptNumber"
        )

        callback_amount = metadata.get("Amount")

        if not receipt or callback_amount is None:
            attempt.status = "failed"
            attempt.result_description = (
                "Successful callback was missing "
                "required payment metadata."
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        try:
            callback_amount = Decimal(
                str(callback_amount)
            )
        except (InvalidOperation, TypeError, ValueError):
            attempt.status = "failed"
            attempt.result_description = (
                "Daraja callback contained an invalid amount."
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        if callback_amount != attempt.amount:
            attempt.status = "failed"
            attempt.result_description = (
                "Daraja callback amount did not match "
                "the expected payment amount."
            )

            attempt.save(
                update_fields=[
                    "callback_payload",
                    "result_code",
                    "result_description",
                    "merchant_request_id",
                    "status",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted",
                },
                status=status.HTTP_200_OK,
            )

        attempt.mpesa_receipt_number = str(
            receipt
        )

        attempt.status = "successful"

        # The payment is confirmed, but accounting settlement
        # has not run yet.
        attempt.settlement_status = "unsettled"

        attempt.completed_at = timezone.now()

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

        return Response(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            },
            status=status.HTTP_200_OK,
        )