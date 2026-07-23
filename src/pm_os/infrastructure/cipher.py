import base64
import os
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


_FERNET_PREFIX = "fernet:"

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


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(_ensure_key()).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return _FERNET_PREFIX + token


def decrypt(encrypted: str) -> str:
    if not encrypted:
        return ""
    if encrypted.startswith(_FERNET_PREFIX):
        try:
            token = encrypted[len(_FERNET_PREFIX):].encode("ascii")
            return _fernet().decrypt(token).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError):
            raise ValueError("Encrypted configuration value could not be authenticated.")
    # Backward-compatible read for values created before authenticated
    # encryption was introduced. ConfigManager rewrites them on the next save.
    try:
        raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))
    except Exception:
        return encrypted  # not encrypted, return as-is
    salt, ciphertext = raw[:16], raw[16:]
    key = _derive_key(salt)
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, key * (len(ciphertext) // len(key) + 1)))
    return plaintext.decode("utf-8")
