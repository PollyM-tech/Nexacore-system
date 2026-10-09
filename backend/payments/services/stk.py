import base64
from datetime import datetime

import requests
from django.utils import timezone

from .daraja import DarajaClient, DarajaError


class StkPushError(Exception):
    """Raised when an STK Push request cannot be initiated."""


class StkPushService:
    """
    Safaricom M-Pesa Express / STK Push service.

    This service only initiates the payment request.

    It does NOT:
    - mark payments successful
    - settle invoices
    - activate PPPoE
    - activate Hotspot

    Those actions happen only after a confirmed callback or reconciliation.
    """

    STK_PATH = "/mpesa/stkpush/v1/processrequest"

    def __init__(self, configuration):
        self.configuration = configuration
        self.client = DarajaClient(configuration)

    @property
    def stk_url(self):
        return (
            f"{self.client.base_url}"
            f"{self.STK_PATH}"
        )

    def _validate_configuration(self):
        config = self.configuration

        if not config.is_active:
            raise StkPushError(
                "M-Pesa configuration is inactive."
            )

        if not config.shortcode:
            raise StkPushError(
                "M-Pesa shortcode is not configured."
            )

        if not config.passkey:
            raise StkPushError(
                "M-Pesa passkey is not configured."
            )

        if config.payment_mode != "own_shortcode":
            raise StkPushError(
                "This STK service currently supports "
                "ISP-owned shortcode configurations only."
            )

    @staticmethod
    def normalize_phone_number(phone_number):
        """
        Normalize Kenyan numbers to 2547XXXXXXXX / 2541XXXXXXXX.
        """

        value = str(phone_number or "").strip()

        value = (
            value
            .replace(" ", "")
            .replace("-", "")
            .replace("+", "")
        )

        if value.startswith("0"):
            value = f"254{value[1:]}"

        elif value.startswith("7") or value.startswith("1"):
            value = f"254{value}"

        if not value.startswith("254"):
            raise StkPushError(
                "Phone number must be a valid Kenyan M-Pesa number."
            )

        if len(value) != 12:
            raise StkPushError(
                "Phone number must contain 12 digits "
                "after normalization."
            )

        if not value.isdigit():
            raise StkPushError(
                "Phone number contains invalid characters."
            )

        return value

    def _timestamp(self):
        return timezone.localtime().strftime(
            "%Y%m%d%H%M%S"
        )

    def _password(self, timestamp):
        raw_value = (
            f"{self.configuration.shortcode}"
            f"{self.configuration.passkey}"
            f"{timestamp}"
        )

        return base64.b64encode(
            raw_value.encode("utf-8")
        ).decode("utf-8")

    def _transaction_type(self):
        if self.configuration.transaction_type == "till":
            return "CustomerBuyGoodsOnline"

        return "CustomerPayBillOnline"

    def initiate(
        self,
        *,
        phone_number,
        amount,
        account_reference,
        callback_url,
        transaction_desc="Lintech Internet Payment",
    ):
        """
        Initiate an STK Push.

        Returns Safaricom's acknowledgement response.

        A successful acknowledgement only means Safaricom accepted
        the STK request for processing. It does NOT mean the customer
        has paid.
        """

        self._validate_configuration()

        phone_number = self.normalize_phone_number(
            phone_number
        )

        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise StkPushError(
                "STK Push amount must be a whole number."
            )

        if amount <= 0:
            raise StkPushError(
                "STK Push amount must be greater than zero."
            )

        account_reference = str(
            account_reference or ""
        ).strip()

        if not account_reference:
            raise StkPushError(
                "Account reference is required."
            )

        timestamp = self._timestamp()

        try:
            token = self.client.get_access_token()
        except DarajaError as exc:
            raise StkPushError(
                "Unable to authenticate with Daraja."
            ) from exc

        payload = {
            "BusinessShortCode": (
                self.configuration.shortcode
            ),
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": (
                self._transaction_type()
            ),
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.configuration.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": (
                account_reference[:20]
            ),
            "TransactionDesc": (
                transaction_desc[:100]
            ),
        }

        headers = {
            "Authorization": (
                f"Bearer {token.access_token}"
            ),
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.stk_url,
                json=payload,
                headers=headers,
                timeout=20,
            )
        except requests.RequestException as exc:
            raise StkPushError(
                "Unable to connect to Safaricom STK service."
            ) from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise StkPushError(
                "Safaricom returned an invalid STK response."
            ) from exc

        if response.status_code not in (200, 201):
            error_message = (
                response_payload.get("errorMessage")
                or response_payload.get(
                    "ResponseDescription"
                )
                or "STK Push request failed."
            )

            raise StkPushError(error_message)

        checkout_request_id = (
            response_payload.get("CheckoutRequestID")
        )

        merchant_request_id = (
            response_payload.get("MerchantRequestID")
        )

        response_code = str(
            response_payload.get(
                "ResponseCode",
                "",
            )
        )

        if (
            response_code != "0"
            or not checkout_request_id
        ):
            raise StkPushError(
                response_payload.get(
                    "ResponseDescription",
                    "STK Push was not accepted.",
                )
            )

        return {
            "merchant_request_id": (
                merchant_request_id
            ),
            "checkout_request_id": (
                checkout_request_id
            ),
            "response_code": response_code,
            "response_description": (
                response_payload.get(
                    "ResponseDescription",
                    "",
                )
            ),
            "customer_message": (
                response_payload.get(
                    "CustomerMessage",
                    "",
                )
            ),
        }