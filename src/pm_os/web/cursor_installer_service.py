"""Safely install PM Studio as a local Cursor MCP server."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path


class CursorInstallerError(ValueError):
    """Raised when Cursor configuration cannot be changed safely."""


class CursorInstallerService:
    """Merge PM Studio into Cursor's MCP config without losing user settings."""

    SERVER_NAME = "pm-studio"

    def __init__(
        self,
        cursor_config_path: Path | str | None = None,
        workspace_dir: Path | str | None = None,
        python_executable: Path | str | None = None,
    ):
        configured_path = cursor_config_path or os.getenv("PM_OS_CURSOR_CONFIG_PATH")
        self.config_path = Path(
            configured_path or Path.home() / ".cursor" / "mcp.json"
        ).expanduser()
        configured_workspace = workspace_dir or os.getenv("PM_OS_WORKSPACE_DIR", "workspace")
        self.workspace_dir = Path(configured_workspace).expanduser().resolve()
        self.python_executable = str(python_executable or sys.executable)

    def desired_entry(self) -> dict:
        return {
            "type": "stdio",
            "command": self.python_executable,
            "args": ["-m", "pm_os.mcp_server"],
            "env": {"PM_OS_WORKSPACE_DIR": str(self.workspace_dir)},
        }

    def status(self) -> dict:
        if not self.config_path.exists():
            return self._status("not_installed")
        try:
            config = self._read_config()
        except CursorInstallerError as exc:
            return self._status("invalid", error=str(exc))
        current = config.get("mcpServers", {}).get(self.SERVER_NAME)
        if current is None:
            return self._status("not_installed")
        if current == self.desired_entry():
            return self._status("installed")
        return self._status("outdated")

    def install(self) -> dict:
        existed = self.config_path.exists()
        config = self._read_config() if existed else {}
        servers = config.get("mcpServers")
        if servers is None:
            servers = {}
            config["mcpServers"] = servers
        if not isinstance(servers, dict):
            raise CursorInstallerError("Cursor mcpServers must be a JSON object.")

        desired = self.desired_entry()
        if servers.get(self.SERVER_NAME) == desired:
            return self._status("installed", changed=False)

        backup_path = None
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        if existed:
            backup_path = self.config_path.with_name(
                f"{self.config_path.name}.pm-studio.bak"
            )
            if not backup_path.exists():
                shutil.copy2(self.config_path, backup_path)

        servers[self.SERVER_NAME] = deepcopy(desired)
        self._write_atomic(config)
        return self._status(
            "installed",
            changed=True,
            backup_path=str(backup_path) if backup_path else "",
        )

    def _read_config(self) -> dict:
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CursorInstallerError("Cursor mcp.json contains invalid JSON.") from exc
        except OSError as exc:
            raise CursorInstallerError("Cursor mcp.json could not be read.") from exc
        if not isinstance(config, dict):
            raise CursorInstallerError("Cursor mcp.json must contain a JSON object.")
        servers = config.get("mcpServers")
        if servers is not None and not isinstance(servers, dict):
            raise CursorInstallerError("Cursor mcpServers must be a JSON object.")
        return config

    def _write_atomic(self, config: dict) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(self.config_path.parent),
                delete=False,
                suffix=".tmp",
                encoding="utf-8",
            ) as handle:
                json.dump(config, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temporary = Path(handle.name)
            temporary.replace(self.config_path)
        except OSError as exc:
            if temporary and temporary.exists():
                temporary.unlink(missing_ok=True)
            raise CursorInstallerError("Cursor mcp.json could not be updated.") from exc

    def _status(self, state: str, **extra: object) -> dict:
        return {
            "state": state,
            "config_path": str(self.config_path),
            **extra,
        }
