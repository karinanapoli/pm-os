import base64
import os
import hashlib
from pathlib import Path


def _get_key_path() -> Path:
    from pm_os.web.config_manager import _get_config_dir
    return _get_config_dir() / ".cipher_key"


def _ensure_key() -> bytes:
    key_path = _get_key_path()
    if key_path.exists():
        return key_path.read_bytes()
    key = os.urandom(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    return key


def _derive_key(salt: bytes) -> bytes:
    master = _ensure_key()
    return hashlib.pbkdf2_hmac("sha256", master, salt, 100_000, dklen=32)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    salt = os.urandom(16)
    key = _derive_key(salt)
    ciphertext = bytes(a ^ b for a, b in zip(plaintext.encode("utf-8"), key * (len(plaintext) // len(key) + 1)))
    return base64.urlsafe_b64encode(salt + ciphertext).decode("ascii")


def decrypt(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))
    except Exception:
        return encrypted  # not encrypted, return as-is
    salt, ciphertext = raw[:16], raw[16:]
    key = _derive_key(salt)
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, key * (len(ciphertext) // len(key) + 1)))
    return plaintext.decode("utf-8")
