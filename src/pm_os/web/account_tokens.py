"""One-time account token helpers that never persist raw secrets."""

import hashlib
import hmac
from typing import Any


def token_digest(
    secret: str,
    purpose: str,
    subject: str,
    token: str,
) -> str:
    message = "\0".join((purpose, subject, token)).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def token_matches(
    expected_digest: object,
    secret: str,
    purpose: str,
    subject: str,
    token: str,
) -> bool:
    if not isinstance(expected_digest, str) or not expected_digest:
        return False
    actual = token_digest(secret, purpose, subject, token)
    return hmac.compare_digest(expected_digest, actual)


def prune_expired(records: dict[str, Any], now: float) -> dict[str, Any]:
    return {
        key: value
        for key, value in records.items()
        if isinstance(value, dict) and value.get("expires_at", 0) >= now
    }
