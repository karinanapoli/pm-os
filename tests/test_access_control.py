from pm_os.web.access_control import (
    assign_initial_admin,
    installation_admins,
    is_installation_admin,
    remove_admin_and_transfer,
    stdio_mcp_enabled,
)


def test_legacy_install_uses_first_user_as_admin():
    config = {"users": {"owner@example.com": "hash", "member@example.com": "hash"}}

    assert installation_admins(config) == ["owner@example.com"]
    assert is_installation_admin(config, "owner@example.com") is True
    assert is_installation_admin(config, "member@example.com") is False


def test_local_single_user_quickstart_remains_administrator():
    config = {"users": {}, "auth_bypass_localhost": True}

    assert is_installation_admin(config, "local@localhost") is True


def test_first_registration_assigns_admin_and_deletion_transfers_role():
    config = {"users": {"owner@example.com": "hash"}, "installation_admins": []}
    assign_initial_admin(config, "owner@example.com", had_users=False)
    config["users"]["member@example.com"] = "hash"

    del config["users"]["owner@example.com"]
    remove_admin_and_transfer(config, "owner@example.com")

    assert config["installation_admins"] == ["member@example.com"]


def test_stdio_requires_explicit_operator_opt_in(monkeypatch):
    monkeypatch.delenv("PM_OS_ENABLE_STDIO_MCP", raising=False)
    assert stdio_mcp_enabled() is False

    monkeypatch.setenv("PM_OS_ENABLE_STDIO_MCP", "true")
    assert stdio_mcp_enabled() is True
