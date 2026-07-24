import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, TypeVar

from pm_os.infrastructure.cipher import decrypt, encrypt

_SENSITIVE_KEYS = frozenset({"openai_api_key", "anthropic_api_key", "auth_password", "smtp_password"})
_T = TypeVar("_T")

def _get_config_dir() -> Path:
    return Path(os.getenv("PM_OS_CONFIG_DIR", str(Path.home() / ".pm_os")))


def _get_config_file() -> Path:
    return _get_config_dir() / "config.json"

SCHEMA: dict[str, type] = {
    "model": str,
    "ollama_url": str,
    "lang": str,
    "onboarding_dismissed": bool,
    "mcp_servers": list,
    "auth_enabled": bool,
    "auth_bypass_localhost": bool,
    "auth_username": str,
    "auth_password": str,
    "ai_provider": str,
    "openai_api_key": str,
    "openai_model": str,
    "anthropic_api_key": str,
    "anthropic_model": str,
    "custom_providers": list,
    "users": dict,
    "pending_registrations": dict,
    "reset_tokens": dict,
    "squads": dict,
    "retired_squad_names": list,
    "smtp_host": str,
    "smtp_port": str,
    "smtp_user": str,
    "smtp_password": str,
    "smtp_from_email": str,
    "smtp_from_name": str,
}

DEFAULT_CONFIG: dict[str, Any] = {
    "model": "llama3.2:1b",
    "ollama_url": "http://localhost:11434",
    "lang": "pt-BR",
    "onboarding_dismissed": False,
    "mcp_servers": [],
    "auth_enabled": False,
    "auth_bypass_localhost": True,
    "auth_username": "",
    "auth_password": "",
    "ai_provider": "demo",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "anthropic_api_key": "",
    "anthropic_model": "claude-3-haiku-20240307",
    "custom_providers": [],
    "users": {},
    "pending_registrations": {},
    "reset_tokens": {},
    "squads": {},
    "retired_squad_names": [],
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from_email": "",
    "smtp_from_name": "PM Studio",
}


def _validate(key: str, value: Any) -> None:
    expected = SCHEMA.get(key)
    if expected is not None and not isinstance(value, expected):
        raise TypeError(f"Config '{key}' must be {expected.__name__}, got {type(value).__name__}")


class ConfigManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._config = self._load()

    def get(self, key: str, default=None):
        with self._lock:
            return deepcopy(self._config.get(key, default))

    def get_all(self) -> dict:
        with self._lock:
            return deepcopy(self._config)

    def set(self, key: str, value: Any) -> None:
        _validate(key, value)
        with self._lock:
            updated = deepcopy(self._config)
            updated[key] = deepcopy(value)
            self._commit(updated)

    def set_all(self, updates: dict) -> None:
        for k, v in updates.items():
            _validate(k, v)
        with self._lock:
            updated = deepcopy(self._config)
            updated.update(deepcopy(updates))
            self._commit(updated)

    def update(self, key: str, updater: Callable[[Any], Any]) -> Any:
        """Atomically transform one setting and return a detached result."""
        with self._lock:
            updated = deepcopy(self._config)
            new_value = updater(deepcopy(updated.get(key)))
            _validate(key, new_value)
            updated[key] = deepcopy(new_value)
            self._commit(updated)
            return deepcopy(new_value)

    def transaction(self, updater: Callable[[dict], _T]) -> _T:
        """Atomically transform multiple settings or leave state unchanged."""
        with self._lock:
            updated = deepcopy(self._config)
            result = updater(updated)
            for key, value in updated.items():
                _validate(key, value)
            self._commit(updated)
            return deepcopy(result)

    def _commit(self, updated: dict) -> bool:
        if updated == self._config and _get_config_file().exists():
            return False
        self._save(updated)
        self._config = updated
        return True

    def _load(self) -> dict:
        config_file = _get_config_file()
        if config_file.exists():
            try:
                raw = json.loads(config_file.read_text(encoding="utf-8"))
                for key in _SENSITIVE_KEYS:
                    if key in raw and raw[key]:
                        try:
                            raw[key] = decrypt(raw[key])
                        except Exception:
                            pass  # legacy plaintext value — will be encrypted on next save
                for cp in raw.get("custom_providers") or []:
                    if cp.get("api_key"):
                        try:
                            cp["api_key"] = decrypt(cp["api_key"])
                        except Exception:
                            pass
                merged = {**DEFAULT_CONFIG, **raw}
                return {k: v for k, v in merged.items() if k in DEFAULT_CONFIG}
            except (json.JSONDecodeError, OSError):
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def _save(self, config: dict) -> None:
        config_dir = _get_config_dir()
        config_file = _get_config_file()
        config_dir.mkdir(parents=True, exist_ok=True)
        to_save = deepcopy(config)
        for key in _SENSITIVE_KEYS:
            if key in to_save and to_save[key]:
                to_save[key] = encrypt(to_save[key])
        for cp in to_save.get("custom_providers") or []:
            if cp.get("api_key"):
                cp["api_key"] = encrypt(cp["api_key"])
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(config_dir),
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        )
        tmp_path = Path(tmp.name)
        try:
            json.dump(to_save, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            if hasattr(os, "fchmod"):
                os.fchmod(tmp.fileno(), 0o600)
            tmp.close()
            tmp_path.chmod(0o600)
            os.replace(tmp.name, str(config_file))
            self._sync_directory(config_dir)
        except Exception:
            if not tmp.closed:
                tmp.close()
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _sync_directory(config_dir: Path) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        try:
            directory_fd = os.open(str(config_dir), flags)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        finally:
            os.close(directory_fd)
