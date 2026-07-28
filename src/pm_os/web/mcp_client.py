"""Small MCP Streamable HTTP client used for safe capability discovery."""

from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass
from typing import Callable, Optional

from pm_os.web.safe_http import PublicHTTPResponse, request_public_url

PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class MCPAuthorizationRequired(MCPError):
    pass


@dataclass(frozen=True)
class MCPDiscovery:
    protocol_version: str
    server_name: str
    server_version: str
    tools: list[dict]
    resources_supported: bool
    prompts_supported: bool

    def as_dict(self) -> dict:
        return {
            "protocol_version": self.protocol_version,
            "server_name": self.server_name,
            "server_version": self.server_version,
            "tools": self.tools,
            "resources_supported": self.resources_supported,
            "prompts_supported": self.prompts_supported,
        }


class MCPClient:
    def __init__(
        self,
        requester: Callable[..., PublicHTTPResponse] = request_public_url,
        timeout: float = 8,
    ):
        self.requester = requester
        self.timeout = timeout
        self._request_id = 0

    def discover(self, connection: dict) -> MCPDiscovery:
        session_id: Optional[str] = None
        try:
            initialized = self._call(connection, "initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "PM Studio", "version": "0.1.0"},
            })
            session_id = initialized[1]
            result = initialized[0]
            self._notify(connection, "notifications/initialized", session_id)
            capabilities = result.get("capabilities") or {}
            tools = []
            if "tools" in capabilities:
                tools = (self._call(connection, "tools/list", {}, session_id)[0].get("tools") or [])
            server_info = result.get("serverInfo") or {}
            return MCPDiscovery(
                protocol_version=str(result.get("protocolVersion") or PROTOCOL_VERSION),
                server_name=str(server_info.get("name") or connection.get("name") or "MCP"),
                server_version=str(server_info.get("version") or ""),
                tools=[
                    {"name": str(tool.get("name", "")), "description": str(tool.get("description", ""))[:300]}
                    for tool in tools
                    if tool.get("name")
                ],
                resources_supported="resources" in capabilities,
                prompts_supported="prompts" in capabilities,
            )
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise MCPAuthorizationRequired(
                    "O servidor exige autorização. Revise a autenticação da conexão."
                ) from exc
            raise MCPError(f"O servidor MCP respondeu com HTTP {exc.code}.") from exc

    def _headers(self, connection: dict, session_id: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        auth = connection.get("auth") or {}
        secret = str(auth.get("secret") or "")
        if auth.get("type") == "bearer" and secret:
            headers["Authorization"] = f"Bearer {secret}"
        elif auth.get("type") == "api_key" and secret:
            headers[str(auth.get("header") or "X-API-Key")] = secret
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return headers

    def _call(
        self,
        connection: dict,
        method: str,
        params: dict,
        session_id: Optional[str] = None,
    ) -> tuple[dict, Optional[str]]:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        response = self.requester(
            connection["url"],
            method="POST",
            headers=self._headers(connection, session_id),
            body=json.dumps(payload).encode("utf-8"),
            timeout=self.timeout,
        )
        message = self._decode(response)
        if message.get("error"):
            error = message["error"]
            raise MCPError(str(error.get("message") or "O servidor MCP retornou um erro.")[:300])
        if not isinstance(message.get("result"), dict):
            raise MCPError("Resposta MCP inválida: campo result ausente.")
        return message["result"], response.headers.get("mcp-session-id") or session_id

    def _notify(self, connection: dict, method: str, session_id: Optional[str]) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        self.requester(
            connection["url"],
            method="POST",
            headers=self._headers(connection, session_id),
            body=json.dumps(payload).encode("utf-8"),
            timeout=self.timeout,
        )

    @staticmethod
    def _decode(response: PublicHTTPResponse) -> dict:
        text = response.body.decode("utf-8", errors="replace").strip()
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type or text.startswith("event:") or text.startswith("data:"):
            data_lines = [
                line[5:].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            ]
            if not data_lines:
                raise MCPError("Resposta SSE do servidor MCP sem dados.")
            text = data_lines[-1]
        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            raise MCPError("O servidor não retornou uma resposta MCP válida.") from exc
        if not isinstance(message, dict):
            raise MCPError("O servidor não retornou um objeto MCP válido.")
        return message
