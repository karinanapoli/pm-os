"""Copy-ready MCP configurations for editors and agents other than Cursor."""

from __future__ import annotations

import json
from pm_os.web.cursor_installer_service import CursorInstallerService


def external_tool_configs(installer: CursorInstallerService | None = None) -> list[dict]:
    """Return one entry per tool with where to paste and the exact snippet.

    All tools run the same local PM Studio MCP server that the Cursor installer
    registers, so the command, arguments and workspace always match.
    """
    entry = (installer or CursorInstallerService()).desired_entry()
    name = CursorInstallerService.SERVER_NAME
    generic = {"command": entry["command"], "args": entry["args"]}
    command = " ".join([entry["command"], *entry["args"]])
    configs = [
        {
            "id": "vscode",
            "name": "VS Code",
            "location": ".vscode/mcp.json",
            "snippet": json.dumps({"servers": {name: entry}}, indent=2, ensure_ascii=False),
        },
        {
            "id": "claude-code",
            "name": "Claude Code",
            "location": "terminal",
            "snippet": f"claude mcp add {name} -- {command}",
        },
        {
            "id": "generic",
            "name": "Claude Desktop, Windsurf",
            "location": "mcpServers",
            "snippet": json.dumps({"mcpServers": {name: generic}}, indent=2, ensure_ascii=False),
        },
    ]
    for config in configs:
        config["masked_snippet"] = config["snippet"]
    return configs
