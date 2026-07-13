import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(os.getenv("PM_OS_CONFIG_DIR", str(Path.home() / ".pm_os")))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "model": "llama3.2:1b",
    "ollama_url": "http://localhost:11434",
    "lang": "pt-BR",
    "onboarding_dismissed": False,
    "mcp_servers": [],
}


class ConfigManager:
    """
    Manages PM OS configuration persisted in ~/.pm_os/config.json.
    """

    def __init__(self):
        self._config = self._load()

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def get_all(self) -> dict:
        return dict(self._config)

    def set(self, key: str, value: str) -> None:
        self._config[key] = value
        self._save()

    def set_all(self, updates: dict) -> None:
        self._config.update(updates)
        self._save()

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text())}
            except (json.JSONDecodeError, OSError):
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
