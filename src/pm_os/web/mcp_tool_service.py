"""Governed, explicit MCP tool execution for the initiative assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pm_os.web.mcp_client import MCPClient, MCPError


@dataclass(frozen=True)
class MCPToolResult:
    connection_name: str
    tool_name: str
    content: str


class MCPToolService:
    def __init__(self, client: Optional[MCPClient] = None, max_result_chars: int = 12_000):
        self.client = client or MCPClient()
        self.max_result_chars = max(1000, max_result_chars)

    def available_tools(self, connections: list[dict]) -> list[dict]:
        tools = []
        for connection in connections:
            if not self._executable(connection):
                continue
            for tool in (connection.get("capabilities") or {}).get("tools") or []:
                name = str(tool.get("name") or "").strip()
                if name:
                    tools.append({
                        "value": f"{connection.get('id', '')}::{name}",
                        "connection": str(connection.get("name") or "MCP"),
                        "name": name,
                        "description": str(tool.get("description") or "")[:300],
                    })
        return tools

    def execute(
        self,
        connections: list[dict],
        selection: str,
        arguments_json: str,
    ) -> MCPToolResult:
        connection_id, separator, tool_name = selection.partition("::")
        if not separator or not connection_id or not tool_name:
            raise MCPError("Selecione uma ferramenta MCP válida.")
        connection = next(
            (item for item in connections if item.get("id") == connection_id),
            None,
        )
        if not connection or not self._executable(connection):
            raise MCPError("Esta conexão MCP não está disponível para consulta.")
        allowed = {
            str(tool.get("name") or "")
            for tool in (connection.get("capabilities") or {}).get("tools") or []
        }
        if tool_name not in allowed:
            raise MCPError("A ferramenta MCP selecionada não foi autorizada pela conexão.")
        try:
            arguments = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            raise MCPError("Os parâmetros da ferramenta devem estar em JSON válido.") from exc
        if not isinstance(arguments, dict):
            raise MCPError("Os parâmetros da ferramenta devem formar um objeto JSON.")
        raw = self.client.call_tool(connection, tool_name, arguments)
        serialized = json.dumps(raw, ensure_ascii=False, indent=2)
        return MCPToolResult(
            connection_name=str(connection.get("name") or "MCP"),
            tool_name=tool_name,
            content=serialized[:self.max_result_chars],
        )

    @staticmethod
    def _executable(connection: dict) -> bool:
        return bool(
            connection.get("enabled")
            and connection.get("type") == "mcp"
            and connection.get("url")
            and (connection.get("policy") or {}).get("mode") == "read_only"
            and (connection.get("capabilities") or {}).get("tools")
        )
