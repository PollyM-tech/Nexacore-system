"""Defensive read-time redaction for historical audit metadata."""
import re


def sensitive_key(key):
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return normalized in {"pass", "pwd"} or any(part in normalized for part in (
        "password", "passwd", "secret", "token", "apikey", "pppoepass",
        "credential", "authorization", "privatekey", "encryptionkey", "community",
        "passkey", "consumerkey", "signingkey",
    ))


def redact_metadata(value):
    if isinstance(value, dict):
        # Also recognize RADIUS-style attribute/value credential records.
        credential_record = any(
            str(key).lower() in {"attribute", "key", "name"}
            and isinstance(item, str) and sensitive_key(item)
            for key, item in value.items()
        )
        return {
            key: "[REDACTED]" if sensitive_key(key) or (
                credential_record and str(key).lower() in {"value", "values"}
            ) else redact_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_metadata(item) for item in value]
    return value
