import json

import pytest

from pm_os.web.cursor_installer_service import (
    CursorInstallerError,
    CursorInstallerService,
)


def _service(tmp_path):
    return CursorInstallerService(
        cursor_config_path=tmp_path / ".cursor" / "mcp.json",
        workspace_dir=tmp_path / "workspace",
        python_executable="/opt/pm-studio/python",
    )


def test_installs_pm_studio_in_new_cursor_config(tmp_path):
    service = _service(tmp_path)

    result = service.install()
    stored = json.loads(service.config_path.read_text(encoding="utf-8"))

    assert result["state"] == "installed"
    assert result["changed"] is True
    assert stored["mcpServers"]["pm-studio"] == service.desired_entry()
    assert service.status()["state"] == "installed"


def test_preserves_existing_cursor_settings_and_creates_backup(tmp_path):
    service = _service(tmp_path)
    service.config_path.parent.mkdir(parents=True)
    original = {
        "customSetting": True,
        "mcpServers": {"github": {"type": "http", "url": "https://example.test"}},
    }
    service.config_path.write_text(json.dumps(original), encoding="utf-8")

    result = service.install()
    stored = json.loads(service.config_path.read_text(encoding="utf-8"))
    backup = service.config_path.with_name("mcp.json.pm-studio.bak")

    assert stored["customSetting"] is True
    assert stored["mcpServers"]["github"] == original["mcpServers"]["github"]
    assert json.loads(backup.read_text(encoding="utf-8")) == original
    assert result["backup_path"] == str(backup)


def test_install_is_idempotent_and_does_not_replace_backup(tmp_path):
    service = _service(tmp_path)
    service.config_path.parent.mkdir(parents=True)
    service.config_path.write_text('{"mcpServers": {}}', encoding="utf-8")
    service.install()
    backup = service.config_path.with_name("mcp.json.pm-studio.bak")
    backup_before = backup.read_text(encoding="utf-8")

    result = service.install()

    assert result["changed"] is False
    assert backup.read_text(encoding="utf-8") == backup_before


def test_reports_existing_pm_studio_entry_as_outdated(tmp_path):
    service = _service(tmp_path)
    service.config_path.parent.mkdir(parents=True)
    service.config_path.write_text(
        json.dumps({"mcpServers": {"pm-studio": {"command": "old"}}}),
        encoding="utf-8",
    )

    assert service.status()["state"] == "outdated"


def test_invalid_json_is_never_overwritten(tmp_path):
    service = _service(tmp_path)
    service.config_path.parent.mkdir(parents=True)
    service.config_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(CursorInstallerError, match="invalid JSON"):
        service.install()

    assert service.config_path.read_text(encoding="utf-8") == "{invalid"


def test_invalid_mcp_servers_is_never_overwritten(tmp_path):
    service = _service(tmp_path)
    service.config_path.parent.mkdir(parents=True)
    service.config_path.write_text('{"mcpServers": []}', encoding="utf-8")

    with pytest.raises(CursorInstallerError, match="JSON object"):
        service.install()

    assert service.config_path.read_text(encoding="utf-8") == '{"mcpServers": []}'


def test_external_tool_configs_reuse_the_pm_studio_mcp_entry(tmp_path):
    import json
    from pm_os.web.external_tool_configs import external_tool_configs

    installer = CursorInstallerService(
        cursor_config_path=tmp_path / "mcp.json",
        workspace_dir=tmp_path / "work space",
        python_executable="/usr/bin/python3",
    )

    configs = {item["id"]: item for item in external_tool_configs(installer)}

    vscode = json.loads(configs["vscode"]["snippet"])["servers"]["pm-studio"]
    assert vscode == installer.desired_entry()
    generic = json.loads(configs["generic"]["snippet"])["mcpServers"]["pm-studio"]
    assert generic["args"] == []
    assert "type" not in generic
    assert configs["claude-code"]["snippet"] == "claude mcp add pm-studio -- pm-studio-mcp"
    for config in configs.values():
        assert str(tmp_path) not in config["masked_snippet"]
        assert "/usr/bin/python3" not in config["masked_snippet"]
        assert "PM_OS_WORKSPACE_DIR" not in config["masked_snippet"]
        assert "pm-studio-mcp" in config["masked_snippet"]
