"""Installation-wide authorization policies, independent from FastAPI routes."""

from __future__ import annotations

import os


def installation_admins(config: dict) -> list[str]:
    """Return valid admins, migrating legacy installs to their first user."""
    users = config.get("users") or {}
    configured = config.get("installation_admins") or []
    valid = [email for email in configured if email in users]
    if valid:
        return valid
    return [next(iter(users))] if users else []


def is_installation_admin(config: dict, email: str) -> bool:
    if (
        not (config.get("users") or {})
        and config.get("auth_bypass_localhost", False)
        and email == "local@localhost"
    ):
        return True
    return bool(email) and email in installation_admins(config)


def assign_initial_admin(config: dict, email: str, had_users: bool) -> None:
    if not had_users:
        config["installation_admins"] = [email]


def remove_admin_and_transfer(config: dict, email: str) -> None:
    users = config.get("users") or {}
    remaining = [item for item in (config.get("installation_admins") or []) if item != email and item in users]
    if not remaining and users:
        remaining = [next(iter(users))]
    config["installation_admins"] = remaining


def stdio_mcp_enabled() -> bool:
    """Local MCP commands are an explicit, operator-controlled capability."""
    return os.getenv("PM_OS_ENABLE_STDIO_MCP", "").strip().lower() in {"1", "true", "yes"}
