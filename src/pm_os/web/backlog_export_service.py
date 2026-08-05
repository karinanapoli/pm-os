"""Governed preparation and confirmation of portable backlog exports."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


EXPORT_TARGETS = frozenset({"github", "linear", "plane", "generic"})


class BacklogExportService:
    def items(self, content: str) -> list[dict]:
        current_epic = ""
        found = []
        blocks = re.split(r"(?=^##(?:#)?\s+)", content, flags=re.MULTILINE)
        for block in blocks:
            epic = re.match(r"^##\s+Épico:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
            if epic:
                current_epic = epic.group(1).strip()
                continue
            story = re.match(r"^###\s+História:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
            if not story:
                continue
            title = story.group(1).strip()
            identifier = hashlib.sha256(f"{current_epic}\0{title}".encode()).hexdigest()[:12]
            found.append({
                "id": identifier,
                "title": title,
                "epic": current_epic or "Backlog",
                "description": block.strip(),
            })
        return found

    def prepare(
        self,
        initiative_path: Path,
        *,
        initiative_name: str,
        target: str,
        selected_ids: list[str],
        actor: str,
    ) -> dict:
        if target not in EXPORT_TARGETS:
            raise ValueError("Invalid export target.")
        state = self._specification(initiative_path)
        if ((state.get("artifacts") or {}).get("backlog") or {}).get("review_status") != "approved":
            raise ValueError("Backlog must be approved before export.")
        backlog_path = initiative_path / "artifacts" / "backlog.md"
        content = backlog_path.read_text(encoding="utf-8") if backlog_path.is_file() else ""
        available = self.items(content)
        allowed = set(selected_ids)
        selected = [item for item in available if item["id"] in allowed]
        if not selected:
            raise ValueError("Select at least one backlog item.")
        payload_items = [self._map_item(item, target, initiative_name) for item in selected]
        preview_id = hashlib.sha256(
            json.dumps(payload_items, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16]
        preview = {
            "preview_id": preview_id,
            "status": "prepared",
            "target": target,
            "initiative": initiative_name,
            "prepared_at": self._now(),
            "prepared_by": actor,
            "items": payload_items,
        }
        path = initiative_path / "artifacts" / "backlog-export-preview.json"
        path.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._audit(initiative_path, "prepared", preview, actor)
        return preview

    def confirm(self, initiative_path: Path, *, preview_id: str, actor: str) -> Path:
        preview_path = initiative_path / "artifacts" / "backlog-export-preview.json"
        if not preview_path.is_file():
            raise ValueError("Prepare an export preview first.")
        preview = json.loads(preview_path.read_text(encoding="utf-8"))
        if preview.get("preview_id") != preview_id or preview.get("status") != "prepared":
            raise ValueError("The export preview is no longer valid.")
        preview["status"] = "confirmed"
        preview["confirmed_at"] = self._now()
        preview["confirmed_by"] = actor
        output = initiative_path / "artifacts" / f"backlog-export-{preview['target']}.json"
        output.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._audit(initiative_path, "confirmed", preview, actor)
        return output

    @staticmethod
    def load_preview(initiative_path: Path) -> dict:
        path = initiative_path / "artifacts" / "backlog-export-preview.json"
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _map_item(item: dict, target: str, initiative_name: str) -> dict:
        common = {"source_id": item["id"], "title": item["title"]}
        if target == "github":
            return {**common, "body": item["description"], "labels": ["backlog", item["epic"]]}
        if target == "linear":
            return {**common, "description": item["description"], "project": initiative_name, "team": ""}
        if target == "plane":
            return {**common, "description": item["description"], "module": item["epic"], "project": initiative_name}
        return {**common, "description": item["description"], "epic": item["epic"], "initiative": initiative_name}

    @staticmethod
    def _specification(initiative_path: Path) -> dict:
        path = initiative_path / "artifacts" / "specification.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _audit(self, initiative_path: Path, event: str, preview: dict, actor: str) -> None:
        path = initiative_path / "artifacts" / "backlog-export-audit.json"
        try:
            history = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
        except (OSError, json.JSONDecodeError):
            history = []
        history.append({
            "event": event,
            "preview_id": preview["preview_id"],
            "target": preview["target"],
            "item_count": len(preview["items"]),
            "actor": actor,
            "created_at": self._now(),
        })
        path.write_text(json.dumps(history[-100:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
