from dataclasses import dataclass
from typing import Optional

import requests
from django.core.cache import cache


class DarajaError(Exception):
    """Raised when communication with Safaricom Daraja fails."""


@dataclass
class DarajaToken:
    access_token: str
    expires_in: int


class DarajaClient:
    """
    Low-level Safaricom Daraja client.

    Credentials come from MpesaConfiguration and are stored encrypted
    at rest. Access tokens are cached per payment configuration.
    """

    SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

    TOKEN_PATH = "/oauth/v1/generate"

    def __init__(self, configuration):
        self.configuration = configuration

    @property
    def base_url(self):
        if self.configuration.environment == "production":
            return self.PRODUCTION_BASE_URL

        return self.SANDBOX_BASE_URL

    @property
    def token_url(self):
        return (
            f"{self.base_url}"
            f"{self.TOKEN_PATH}"
            "?grant_type=client_credentials"
        )

    @property
    def token_cache_key(self):
        return (
            "lintech:daraja:access-token:"
            f"{self.configuration.pk}:"
            f"{self.configuration.environment}"
        )

    def _validate_credentials(self):
        if not self.configuration.consumer_key:
            raise DarajaError(
                "Consumer Key is not configured."
            )

        if not self.configuration.consumer_secret:
            raise DarajaError(
                "Consumer Secret is not configured."
            )

    def get_access_token(
        self,
        force_refresh=False,
    ) -> DarajaToken:
        """
        Get a Daraja OAuth access token.

        Tokens are cached per MpesaConfiguration so credentials
        belonging to different ISPs can never share the same token.
        """

        self._validate_credentials()

        if not force_refresh:
            cached_token = cache.get(
                self.token_cache_key
            )

            if cached_token:
                return DarajaToken(
                    access_token=cached_token,
                    expires_in=0,
                )

        try:
            response = requests.get(
                self.token_url,
                auth=(
                    self.configuration.consumer_key,
                    self.configuration.consumer_secret,
                ),
                timeout=15,
            )
        except requests.RequestException as exc:
            raise DarajaError(
                "Unable to connect to Safaricom Daraja."
            ) from exc

        if response.status_code != 200:
            raise DarajaError(
                "Daraja authentication failed."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise DarajaError(
                "Daraja returned an invalid authentication response."
            ) from exc

        access_token = payload.get("access_token")

        if not access_token:
            raise DarajaError(
                "Daraja authentication response did not contain "
                "an access token."
            )

        try:
            expires_in = int(
                payload.get("expires_in", 3599)
            )
        except (TypeError, ValueError):
            expires_in = 3599

        # Leave a safety buffer so we don't use a token that is
        # about to expire during an API request.
        cache_timeout = max(
            60,
            expires_in - 120,
        )

        cache.set(
            self.token_cache_key,
            access_token,
            timeout=cache_timeout,
        )

        return DarajaToken(
            access_token=access_token,
            expires_in=expires_in,
        )

    def test_connection(self) -> dict:
        """
        Verify that the configured Consumer Key and Consumer Secret
        can successfully authenticate with Daraja.

        The access token itself is intentionally never returned.
        """

        token = self.get_access_token(
            force_refresh=True,
        )

        return {
            "success": True,
            "environment": self.configuration.environment,
            "shortcode": self.configuration.shortcode,
            "expires_in": token.expires_in,
        }