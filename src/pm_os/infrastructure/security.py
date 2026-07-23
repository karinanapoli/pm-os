import hashlib
import hmac
import re
from typing import Tuple

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


MIN_PASSWORD_LENGTH = 10
_LEGACY_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> Tuple[bool, bool]:
    """Return (valid, needs_rehash), accepting legacy SHA-256 hashes once."""
    if not stored_hash:
        return False, False
    if _LEGACY_SHA256.fullmatch(stored_hash):
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(stored_hash, legacy), True
    try:
        valid = _hasher.verify(stored_hash, password)
        return valid, valid and _hasher.check_needs_rehash(stored_hash)
    except (InvalidHashError, VerifyMismatchError):
        return False, False


def password_is_strong(password: str) -> bool:
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and any(char.isalpha() for char in password)
        and any(char.isdigit() for char in password)
    )
