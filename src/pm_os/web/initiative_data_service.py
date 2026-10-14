"""Initiative-scoped spreadsheets and external automation registrations."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path


class InitiativeDataService:
    def list_spreadsheets(self, initiative_path: Path) -> list[dict]:
        return self._load(initiative_path, "spreadsheets.json")

    def add_spreadsheet(self, initiative_path: Path, filename: str, content: bytes) -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".csv", ".tsv"}:
            raise ValueError("unsupported_spreadsheet")
        text = content.decode("utf-8-sig")
        delimiter = "\t" if suffix == ".tsv" else ","
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        if not rows:
            raise ValueError("empty_spreadsheet")
        entry = {
            "name": Path(filename).name,
            "rows": max(len(rows) - 1, 0),
            "columns": len(rows[0]),
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        items = self.list_spreadsheets(initiative_path)
        items = [item for item in items if item.get("name") != entry["name"]]
        items.append(entry)
        self._save(initiative_path, "spreadsheets.json", items)
        return entry

    def list_automations(self, initiative_path: Path) -> list[dict]:
        return self._load(initiative_path, "automations.json")

    def register_automation(
        self, initiative_path: Path, *, name: str, tool: str, description: str = ""
    ) -> dict:
        if not name.strip() or not tool.strip():
            raise ValueError("name_and_tool_required")
        items = self.list_automations(initiative_path)
        entry = {
            "id": f"AUT-{len(items) + 1:03d}",
            "name": name.strip(),
            "tool": tool.strip(),
            "description": description.strip(),
            "status": "connected",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        items.append(entry)
        self._save(initiative_path, "automations.json", items)
        return entry

    @staticmethod
    def _data_dir(initiative_path: Path) -> Path:
        return initiative_path / "data-sources"

    def _load(self, initiative_path: Path, filename: str) -> list[dict]:
        path = self._data_dir(initiative_path) / filename
        if not path.is_file():
            return []
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, initiative_path: Path, filename: str, items: list[dict]) -> None:
        directory = self._data_dir(initiative_path)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
