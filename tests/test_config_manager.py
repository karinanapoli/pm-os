import json
import os
from concurrent.futures import ThreadPoolExecutor
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
    assert cm.get("gateway_project_id") == ""


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


def test_get_returns_detached_nested_values(fresh_config):
    cm = ConfigManager()
    cm.set("users", {"person@example.com": "hash"})

    users = cm.get("users")
    users["attacker@example.com"] = "other-hash"
    all_config = cm.get_all()
    all_config["users"].clear()

    assert cm.get("users") == {"person@example.com": "hash"}


def test_atomic_update_preserves_concurrent_mapping_changes(fresh_config):
    cm = ConfigManager()

    def add_user(index):
        email = f"person-{index}@example.com"
        cm.update(
            "users",
            lambda users: {**(users or {}), email: f"hash-{index}"},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(add_user, range(40)))

    users = cm.get("users")
    assert len(users) == 40
    assert users["person-39@example.com"] == "hash-39"


def test_transaction_updates_multiple_keys_together(fresh_config):
    cm = ConfigManager()

    def activate_user(config):
        config["users"]["person@example.com"] = "hash"
        config["pending_registrations"].pop("person@example.com", None)
        return "activated"

    cm.set("pending_registrations", {"person@example.com": {"expires_at": 1}})
    result = cm.transaction(activate_user)

    assert result == "activated"
    assert cm.get("users") == {"person@example.com": "hash"}
    assert cm.get("pending_registrations") == {}


def test_failed_write_keeps_previous_in_memory_state(fresh_config, monkeypatch):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")

    def fail_save(_config):
        raise OSError("disk full")

    monkeypatch.setattr(cm, "_save", fail_save)

    with pytest.raises(OSError):
        cm.set("lang", "en")

    assert cm.get("lang") == "pt-BR"


def test_unchanged_updates_do_not_rewrite_existing_file(
    fresh_config, monkeypatch
):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")
    writes = []
    original_save = cm._save

    def track_save(config):
        writes.append(config)
        original_save(config)

    monkeypatch.setattr(cm, "_save", track_save)

    cm.set("lang", "pt-BR")
    cm.set_all({"lang": "pt-BR"})
    cm.update("users", lambda users: users or {})
    result = cm.transaction(lambda config: "unchanged")

    assert result == "unchanged"
    assert writes == []


def test_changed_transaction_writes_once(fresh_config, monkeypatch):
    cm = ConfigManager()
    cm.set("lang", "pt-BR")
    writes = []
    original_save = cm._save

    def track_save(config):
        writes.append(config)
        original_save(config)

    monkeypatch.setattr(cm, "_save", track_save)

    cm.transaction(lambda config: config.update(lang="en"))

    assert len(writes) == 1
    assert cm.get("lang") == "en"


def test_config_file_permissions_are_private(fresh_config):
    cm = ConfigManager()
    cm.set("lang", "en")
    config_file = Path(os.environ["PM_OS_CONFIG_DIR"]) / "config.json"

    assert config_file.stat().st_mode & 0o777 == 0o600


def test_gateway_api_key_is_encrypted_at_rest(fresh_config):
    cm = ConfigManager()
    cm.set_all({
        "gateway_url": "https://gateway.example/v1",
        "gateway_provider": "openai",
        "gateway_project_id": "pm-studio",
        "gateway_identifier": "gpt-prod",
        "gateway_api_key": "secret-token",
    })
    config_file = Path(os.environ["PM_OS_CONFIG_DIR"]) / "config.json"
    persisted = config_file.read_text(encoding="utf-8")

    assert "secret-token" not in persisted
    assert ConfigManager().get("gateway_api_key") == "secret-token"
