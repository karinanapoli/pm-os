import json
import os
from pathlib import Path

import pytest

from pm_os.web.config_manager import ConfigManager, DEFAULT_CONFIG


@pytest.fixture
def fresh_config(tmp_path):
    os.environ["PM_OS_CONFIG_DIR"] = str(tmp_path / ".pm_os")
    yield
    os.environ.pop("PM_OS_CONFIG_DIR", None)


def test_default_config(fresh_config):
    cm = ConfigManager()
    assert cm.get("lang") == "pt-BR"
    assert cm.get("model") == "llama3.2:1b"
    assert cm.get("mcp_servers") == []


def test_set_and_get(fresh_config):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")
    assert cm.get("lang") == "pt-BR"


def test_get_all(fresh_config):
    cm = ConfigManager()
    all_cfg = cm.get_all()
    assert "lang" in all_cfg
    assert "model" in all_cfg


def test_set_all(fresh_config):
    cm = ConfigManager()
    cm.set_all({"lang": "pt-BR", "model": "qwen2.5:7b"})
    assert cm.get("lang") == "pt-BR"
    assert cm.get("model") == "qwen2.5:7b"


def test_persists_to_file(fresh_config):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")
    config_dir = Path(os.environ["PM_OS_CONFIG_DIR"])
    config_file = config_dir / "config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["lang"] == "pt-BR"


def test_loads_from_existing_file(tmp_path):
    config_dir = tmp_path / ".pm_os"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"lang": "pt-BR", "model": "qwen2.5:7b"}), encoding="utf-8"
    )
    os.environ["PM_OS_CONFIG_DIR"] = str(config_dir)
    try:
        cm = ConfigManager()
        assert cm.get("lang") == "pt-BR"
        assert cm.get("model") == "qwen2.5:7b"
    finally:
        os.environ.pop("PM_OS_CONFIG_DIR", None)


def test_merges_with_defaults(tmp_path):
    config_dir = tmp_path / ".pm_os"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"lang": "pt-BR"}), encoding="utf-8"
    )
    os.environ["PM_OS_CONFIG_DIR"] = str(config_dir)
    try:
        cm = ConfigManager()
        assert cm.get("lang") == "pt-BR"
        assert cm.get("model") == "llama3.2:1b"
    finally:
        os.environ.pop("PM_OS_CONFIG_DIR", None)


def test_rejects_wrong_type(fresh_config):
    cm = ConfigManager()
    with pytest.raises(TypeError):
        cm.set("lang", 123)
    with pytest.raises(TypeError):
        cm.set("onboarding_dismissed", "not_bool")


def test_handles_corrupted_file(tmp_path):
    config_dir = tmp_path / ".pm_os"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("invalid json", encoding="utf-8")
    os.environ["PM_OS_CONFIG_DIR"] = str(config_dir)
    try:
        cm = ConfigManager()
        assert cm.get("lang") == "pt-BR"
    finally:
        os.environ.pop("PM_OS_CONFIG_DIR", None)


def test_get_unknown_key(fresh_config):
    cm = ConfigManager()
    assert cm.get("nonexistent") is None
    assert cm.get("nonexistent", "fallback") == "fallback"


def test_atomic_write(fresh_config):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")
    config_dir = Path(os.environ["PM_OS_CONFIG_DIR"])
    config_file = config_dir / "config.json"
    tmp_files = list(config_dir.glob("*.tmp"))
    assert len(tmp_files) == 0
    assert config_file.exists()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["lang"] == "pt-BR"
