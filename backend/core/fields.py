import json

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)
from django.conf import settings
from django.core.exceptions import (
    ImproperlyConfigured,
)
from django.db import models


ENCRYPTED_PREFIX = "lintech:v1:"


def _get_fernet():
    key = getattr(
        settings,
        "LINTECH_FIELD_ENCRYPTION_KEY",
        "",
    )

    if not key:
        raise ImproperlyConfigured(
            "LINTECH_FIELD_ENCRYPTION_KEY "
            "is not configured."
        )

    try:
        if isinstance(key, str):
            key = key.encode("utf-8")

        return Fernet(key)

    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "LINTECH_FIELD_ENCRYPTION_KEY "
            "is invalid."
        ) from exc


def encrypt_value(value):
    if value is None:
        return None

    value = str(value)

    if value == "":
        return value

    if value.startswith(
        ENCRYPTED_PREFIX
    ):
        return value

    token = _get_fernet().encrypt(
        value.encode("utf-8")
    )

    return (
        ENCRYPTED_PREFIX
        + token.decode("utf-8")
    )


def decrypt_value(value):
    if value is None:
        return None

    value = str(value)

    if value == "":
        return value

    # Legacy plaintext values remain readable
    # until a data migration encrypts them.
    if not value.startswith(
        ENCRYPTED_PREFIX
    ):
        return value

    token = value[
        len(ENCRYPTED_PREFIX):
    ]

    try:
        decrypted = _get_fernet().decrypt(
            token.encode("utf-8")
        )

    except InvalidToken as exc:
        raise ValueError(
            "Unable to decrypt "
            "Lintech credential."
        ) from exc

    return decrypted.decode("utf-8")


class EncryptedTextField(
    models.TextField
):
    """
    Reversible encrypted text field.

    Python receives plaintext.
    PostgreSQL stores ciphertext.
    """

    description = (
        "Lintech encrypted text field"
    )

    def from_db_value(
        self,
        value,
        expression,
        connection,
    ):
        return decrypt_value(
            value
        )

    def to_python(
        self,
        value,
    ):
        if value is None:
            return None

        return decrypt_value(
            value
        )

    def get_prep_value(
        self,
        value,
    ):
        value = (
            super()
            .get_prep_value(value)
        )

        return encrypt_value(
            value
        )


class EncryptedJSONField(
    models.TextField
):
    """
    Store a Python JSON-compatible object as
    encrypted ciphertext.

    Application code receives the original
    Python dict/list/value.

    PostgreSQL stores only encrypted text.
    """

    description = (
        "Lintech encrypted JSON field"
    )

    def _deserialize(
        self,
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            (
                dict,
                list,
                int,
                float,
                bool,
            ),
        ):
            return value

        value = str(value)

        if value == "":
            return {}

        plaintext = decrypt_value(
            value
        )

        try:
            return json.loads(
                plaintext
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ) as exc:
            raise ValueError(
                "Unable to decode encrypted "
                "Lintech JSON value."
            ) from exc

    def from_db_value(
        self,
        value,
        expression,
        connection,
    ):
        return self._deserialize(
            value
        )

    def to_python(
        self,
        value,
    ):
        return self._deserialize(
            value
        )

    def get_prep_value(
        self,
        value,
    ):
        if value is None:
            return None

        if isinstance(value, str):
            if value.startswith(
                ENCRYPTED_PREFIX
            ):
                return value

            try:
                parsed = json.loads(
                    value
                )
            except json.JSONDecodeError:
                raise ValueError(
                    "EncryptedJSONField "
                    "requires valid JSON."
                )

            value = parsed

        serialized = json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
        )

        return encrypt_value(
            serialized
        )