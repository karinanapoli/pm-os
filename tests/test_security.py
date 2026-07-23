import hashlib

from pm_os.infrastructure.security import (
    hash_password,
    password_is_strong,
    verify_password,
)


def test_argon2_password_round_trip():
    stored = hash_password("product1234")
    assert stored.startswith("$argon2")
    assert verify_password(stored, "product1234") == (True, False)
    assert verify_password(stored, "wrong-password")[0] is False


def test_legacy_sha256_password_requests_migration():
    stored = hashlib.sha256("product1234".encode()).hexdigest()
    assert verify_password(stored, "product1234") == (True, True)


def test_password_policy_requires_length_letter_and_number():
    assert password_is_strong("product1234")
    assert not password_is_strong("short1")
    assert not password_is_strong("onlyletters")
    assert not password_is_strong("1234567890")
