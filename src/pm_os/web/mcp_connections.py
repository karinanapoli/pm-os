"""Universal, backward-compatible MCP connection configuration."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any

AUTH_TYPES = frozenset({"none", "bearer", "api_key", "oauth"})
CONNECTION_TYPES = frozenset({"mcp", "legacy_http"})
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


def connection_id(url: str) -> str:
    return "mcp-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def businessmap_endpoint(subdomain: str) -> str:
    cleaned = subdomain.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", cleaned):
        raise ValueError("Informe um subdomínio Businessmap válido.")
    return PRESETS["businessmap"]["endpoint_template"].format(subdomain=cleaned)


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
    return {
        "id": connection_id(url),
        "name": name.strip(),
        "url": url,
        "type": connection_type,
        "preset": preset if preset in PRESETS else "custom",
        "transport": "streamable_http" if connection_type == "mcp" else "http_get",
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
    return item
