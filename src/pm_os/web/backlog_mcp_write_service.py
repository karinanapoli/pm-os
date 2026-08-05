"""Governed execution of confirmed backlog packages through MCP write tools."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pm_os.web.mcp_client import MCPClient, MCPError


class BacklogMCPWriteService:
    def __init__(self, client: Optional[MCPClient] = None):
        self.client = client or MCPClient()

    @staticmethod
    def available_tools(connections: list[dict]) -> list[dict]:
        available = []
        for connection in connections:
            if not BacklogMCPWriteService._writable(connection):
                continue
            for tool in (connection.get("capabilities") or {}).get("tools") or []:
                name = str(tool.get("name") or "").strip()
                if name:
                    available.append({
                        "value": f"{connection.get('id', '')}::{name}",
                        "connection": str(connection.get("name") or "MCP"),
                        "name": name,
                        "description": str(tool.get("description") or "")[:300],
                    })
        return available

    def execute(
        self,
        initiative_path: Path,
        *,
        selection: str,
        connections: list[dict],
        actor: str,
    ) -> dict:
        package = self._confirmed_package(initiative_path)
        connection_id, separator, tool_name = selection.partition("::")
        connection = next(
            (item for item in connections if item.get("id") == connection_id), None
        )
        if not separator or not tool_name or not connection or not self._writable(connection):
            raise MCPError("Selecione uma ferramenta MCP habilitada para escrita confirmada.")
        allowed = {
            str(tool.get("name") or "")
            for tool in (connection.get("capabilities") or {}).get("tools") or []
        }
        if tool_name not in allowed:
            raise MCPError("A ferramenta MCP selecionada não pertence a esta conexão.")

        receipt_path = initiative_path / "artifacts" / "backlog-mcp-write-receipt.json"
        receipt = self._load_json(receipt_path, {"executions": []})
        prior = {
            item.get("idempotency_key"): item
            for execution in receipt.get("executions", [])
            for item in execution.get("items", [])
            if item.get("status") == "created"
        }
        results = []
        for item in package["items"]:
            key = self._idempotency_key(package, connection_id, tool_name, item)
            if key in prior:
                results.append({**prior[key], "status": "duplicate_skipped"})
                continue
            try:
                response = self.client.call_tool(
                    connection,
                    tool_name,
                    {"item": item, "idempotency_key": key},
                )
                results.append({
                    "source_id": item.get("source_id"),
                    "title": item.get("title"),
                    "idempotency_key": key,
                    "status": "created",
                    "external_result": self._bounded(response),
                })
            except MCPError as exc:
                results.append({
                    "source_id": item.get("source_id"),
                    "title": item.get("title"),
                    "idempotency_key": key,
                    "status": "failed",
                    "error": str(exc)[:300],
                })

        execution = {
            "execution_id": hashlib.sha256(
                f"{package['preview_id']}\0{connection_id}\0{tool_name}".encode()
            ).hexdigest()[:16],
            "preview_id": package["preview_id"],
            "connection_id": connection_id,
            "connection_name": str(connection.get("name") or "MCP"),
            "tool_name": tool_name,
            "actor": actor,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "items": results,
        }
        receipt.setdefault("executions", []).append(execution)
        receipt["executions"] = receipt["executions"][-50:]
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return execution

    @staticmethod
    def load_receipt(initiative_path: Path) -> dict:
        return BacklogMCPWriteService._load_json(
            initiative_path / "artifacts" / "backlog-mcp-write-receipt.json",
            {},
        )

    @staticmethod
    def _confirmed_package(initiative_path: Path) -> dict:
        preview = BacklogMCPWriteService._load_json(
            initiative_path / "artifacts" / "backlog-export-preview.json", {}
        )
        if preview.get("status") != "confirmed" or not preview.get("items"):
            raise MCPError("Confirme o pacote de exportação antes de enviá-lo via MCP.")
        return preview

    @staticmethod
    def _writable(connection: dict) -> bool:
        return bool(
            connection.get("enabled")
            and connection.get("type") == "mcp"
            and connection.get("url")
            and (connection.get("policy") or {}).get("mode") == "confirm_writes"
            and (connection.get("capabilities") or {}).get("tools")
        )

    @staticmethod
    def _idempotency_key(package: dict, connection_id: str, tool_name: str, item: dict) -> str:
        value = f"{package['preview_id']}\0{connection_id}\0{tool_name}\0{item.get('source_id', '')}"
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _bounded(value: dict) -> dict:
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded) <= 4000:
            return value
        return {"truncated": True, "preview": encoded[:4000]}

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
            return value if isinstance(value, dict) else default
        except (OSError, json.JSONDecodeError):
            return default
