import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.getenv("PM_OS_CONFIG_DIR", str(Path.home() / ".pm_os")))
CONFIG_FILE = CONFIG_DIR / "config.json"

SCHEMA: dict[str, type] = {
    "model": str,
    "ollama_url": str,
    "lang": str,
    "onboarding_dismissed": bool,
    "mcp_servers": list,
    "auth_enabled": bool,
    "auth_username": str,
    "auth_password": str,
    "ai_provider": str,
    "openai_api_key": str,
    "openai_model": str,
    "anthropic_api_key": str,
    "anthropic_model": str,
    "custom_providers": list,
}

DEFAULT_CONFIG: dict[str, Any] = {
    "model": "llama3.2:1b",
    "ollama_url": "http://localhost:11434",
    "lang": "en",
    "onboarding_dismissed": False,
    "mcp_servers": [],
    "auth_enabled": False,
    "auth_username": "",
    "auth_password": "",
    "ai_provider": "ollama",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "anthropic_api_key": "",
    "anthropic_model": "claude-3-haiku-20240307",
    "custom_providers": [],
}


def _validate(key: str, value: Any) -> None:
    expected = SCHEMA.get(key)
    if expected is not None and not isinstance(value, expected):
        raise TypeError(f"Config '{key}' must be {expected.__name__}, got {type(value).__name__}")


class ConfigManager:
    def __init__(self):
        self._config = self._load()

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def get_all(self) -> dict:
        return dict(self._config)

    def set(self, key: str, value: Any) -> None:
        _validate(key, value)
        self._config[key] = value
        self._save()

    def set_all(self, updates: dict) -> None:
        for k, v in updates.items():
            _validate(k, v)
        self._config.update(updates)
        self._save()

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                merged = {**DEFAULT_CONFIG, **raw}
                return {k: v for k, v in merged.items() if k in DEFAULT_CONFIG}
            except (json.JSONDecodeError, OSError):
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
