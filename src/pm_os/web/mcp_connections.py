"""Universal, backward-compatible MCP connection configuration."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any, Optional

AUTH_TYPES = frozenset({"none", "bearer", "api_key", "oauth"})
CONNECTION_TYPES = frozenset({"mcp", "legacy_http", "stdio"})
POLICY_MODES = frozenset({"read_only", "confirm_writes"})
PRESETS = {
    "businessmap": {
        "name": "Businessmap",
        "auth_type": "oauth",
        "endpoint_template": "https://{subdomain}.businessmap.io/baiApi/v1/mcp",
    },
    "custom": {
        "name": "MCP personalizado",
        "auth_type": "none",
    },
    "legacy_http": {
        "name": "Fonte HTTP simples",
        "auth_type": "none",
    },
}
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def connection_id(url: str) -> str:
    return "mcp-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def businessmap_endpoint(subdomain: str) -> str:
    cleaned = subdomain.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", cleaned):
        raise ValueError("Informe um subdomínio Businessmap válido.")
    return PRESETS["businessmap"]["endpoint_template"].format(subdomain=cleaned)


def parse_stdio_args(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def parse_stdio_env(value: str) -> dict[str, str]:
    result = {}
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError("Use o formato NOME=valor nas variáveis de ambiente.")
        key, item_value = line.split("=", 1)
        key = key.strip()
        if not ENV_NAME_RE.fullmatch(key):
            raise ValueError(f"Nome de variável de ambiente inválido: {key}")
        result[key] = item_value
    return result


def build_connection(
    *,
    name: str,
    url: str,
    connection_type: str = "mcp",
    preset: str = "custom",
    auth_type: str = "none",
    auth_secret: str = "",
    auth_header: str = "",
    policy_mode: str = "read_only",
    command: str = "",
    args: Optional[list[str]] = None,
    env: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    if not name.strip():
        raise ValueError("Informe um nome para a conexão.")
    if connection_type not in CONNECTION_TYPES:
        raise ValueError("Tipo de conexão inválido.")
    if auth_type not in AUTH_TYPES:
        raise ValueError("Tipo de autenticação inválido.")
    if policy_mode not in POLICY_MODES:
        raise ValueError("Política de uso inválida.")
    header = auth_header.strip()
    if auth_type == "api_key" and not header:
        header = "X-API-Key"
    if header and not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", header):
        raise ValueError("Nome de header inválido.")
    clean_command = command.strip()
    if connection_type == "stdio" and not clean_command:
        raise ValueError("Informe o comando do servidor stdio.")
    identity = url if connection_type != "stdio" else f"stdio:{clean_command}:{args or []}"
    connection = {
        "id": connection_id(identity),
        "name": name.strip(),
        "url": url,
        "type": connection_type,
        "preset": preset if preset in PRESETS else "custom",
        "transport": (
            "stdio"
            if connection_type == "stdio"
            else "streamable_http"
            if connection_type == "mcp"
            else "http_get"
        ),
        "auth": {
            "type": auth_type,
            "header": header,
            "secret": auth_secret,
        },
        "policy": {
            "mode": policy_mode,
            "allowed_tools": [],
        },
        "capabilities": {},
        "status": {
            "state": "authorization_required" if auth_type == "oauth" else "not_tested",
            "message": "",
        },
        "enabled": True,
    }
    if connection_type == "stdio":
        connection.update({
            "command": clean_command,
            "args": [str(item) for item in (args or []) if str(item)],
            "env": {str(key): str(value) for key, value in (env or {}).items()},
            "status": {"state": "not_tested", "message": ""},
        })
    return connection


def normalize_connection(connection: dict[str, Any]) -> dict[str, Any]:
    """Upgrade old name/url entries in memory without losing compatibility."""
    item = deepcopy(connection)
    url = str(item.get("url", "")).strip()
    if "type" not in item:
        item.update({
            "id": connection_id(url),
            "type": "legacy_http",
            "preset": "legacy_http",
            "transport": "http_get",
            "auth": {"type": "none", "header": "", "secret": ""},
            "policy": {"mode": "read_only", "allowed_tools": []},
            "capabilities": {},
        })
    item.setdefault("id", connection_id(url))
    item.setdefault("enabled", True)
    item.setdefault("capabilities", {})
    item.setdefault("status", {"state": "not_tested", "message": ""})
    item.setdefault(
        "transport",
        "stdio"
        if item.get("type") == "stdio"
        else "streamable_http"
        if item.get("type") == "mcp"
        else "http_get",
    )
    if item.get("type") == "stdio":
        item.setdefault("command", "")
        item.setdefault("args", [])
        item.setdefault("env", {})
    return item


def sanitize_capabilities(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    tools = value.get("tools") if isinstance(value.get("tools"), list) else []
    return {
        "protocol_version": str(value.get("protocol_version") or "")[:30],
        "server_name": str(value.get("server_name") or "")[:100],
        "server_version": str(value.get("server_version") or "")[:50],
        "tools": [
            {
                "name": str(tool.get("name") or "")[:100],
                "description": str(tool.get("description") or "")[:300],
            }
            for tool in tools[:200]
            if isinstance(tool, dict) and tool.get("name")
        ],
        "resources_supported": bool(value.get("resources_supported")),
        "prompts_supported": bool(value.get("prompts_supported")),
    }


def public_connection(connection: dict[str, Any]) -> dict[str, Any]:
    item = normalize_connection(connection)
    auth = dict(item.get("auth") or {})
    auth["secret"] = ""
    auth["has_secret"] = bool((item.get("auth") or {}).get("secret"))
    item["auth"] = auth
    item["env_keys"] = sorted((item.get("env") or {}).keys())
    item["env"] = {}
    return item
