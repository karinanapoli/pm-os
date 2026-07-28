import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import yaml


class InvalidInitiativeId(ValueError):
    pass


class InitiativeLifecycleService:
    """Create, archive, list and restore initiatives outside HTTP routes."""

    def __init__(self, repository, tracker_factory: Callable):
        self.repository = repository
        self.tracker_factory = tracker_factory

    def create(
        self,
        name: str,
        initiative_id: str = "",
        status: str = "discovery",
        context: str = "",
        squad_name: str = "",
        experience_mode: str = "quick",
    ) -> str:
        initiative_id = self._normalize_id(name, initiative_id)
        path = self._available_path(
            self.repository.initiatives_path,
            initiative_id,
            separator="-",
        )
        initiative_id = path.name
        for directory in ("artifacts", "context", "logs"):
            (path / directory).mkdir(parents=True, exist_ok=True)
        metadata = {
            "id": initiative_id,
            "name": name.strip(),
            "status": status,
            "squad": squad_name,
            "created_at": str(date.today()),
            "artifacts": ["prd"],
            "workflows": ["create_prd"],
            "experience_mode": "guided" if experience_mode == "guided" else "quick",
        }
        (path / "metadata.yaml").write_text(
            yaml.dump(metadata, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        if context.strip():
            (path / "context" / "context.md").write_text(
                context.strip(),
                encoding="utf-8",
            )
        self.tracker_factory().update_manifest(str(path))
        return initiative_id

    def archive(self, initiative_name: str) -> Optional[str]:
        initiative = self.repository.get(initiative_name, load_content=False)
        if not initiative or not initiative.path.exists():
            return None
        archive_dir = self.repository.initiatives_path.parent / "archived"
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self._available_path(
            archive_dir,
            f"{initiative_name}_{timestamp}",
            separator="-",
        )
        shutil.move(str(initiative.path), str(destination))
        (destination / ".archive_meta").write_text(
            f"archived_at: {timestamp}\noriginal_name: {initiative_name}\n",
            encoding="utf-8",
        )
        return destination.name

    def list_archived(self) -> list[dict]:
        archive_dir = self.repository.initiatives_path.parent / "archived"
        if not archive_dir.exists():
            return []
        entries = []
        for path in sorted(archive_dir.iterdir(), reverse=True):
            if not path.is_dir():
                continue
            metadata = self._read_archive_metadata(path)
            entries.append({
                "name": path.name,
                "archived_at": metadata.get("archived_at", ""),
            })
        return entries

    def restore(self, archived_name: str) -> Optional[str]:
        clean_name = Path(archived_name).name
        if not clean_name or clean_name != archived_name:
            return None
        archive_dir = self.repository.initiatives_path.parent / "archived"
        source = archive_dir / clean_name
        if not source.is_dir():
            return None
        metadata = self._read_archive_metadata(source)
        original_name = metadata.get("original_name") or clean_name.rsplit("_", 2)[0]
        destination = self._available_path(
            self.repository.initiatives_path,
            original_name,
            separator="-restored-",
        )
        shutil.move(str(source), str(destination))
        self.tracker_factory().update_manifest(str(destination))
        return destination.name

    @staticmethod
    def _normalize_id(name: str, initiative_id: str) -> str:
        if initiative_id.strip():
            cleaned = initiative_id.strip()
            if not re.match(r"^[A-Za-z0-9_-]+$", cleaned):
                raise InvalidInitiativeId(cleaned)
            cleaned = cleaned.strip("-_.")
            if cleaned:
                return cleaned
        safe_name = re.sub(r"[^A-Z0-9]+", "-", name.strip().upper()).strip("-")
        return f"INT-{safe_name[:30]}"

    @staticmethod
    def _available_path(base: Path, name: str, separator: str) -> Path:
        candidate = base / name
        counter = 1
        while candidate.exists():
            candidate = base / f"{name}{separator}{counter:03d}"
            counter += 1
        return candidate

    @staticmethod
    def _read_archive_metadata(path: Path) -> dict:
        metadata = {}
        meta_file = path / ".archive_meta"
        if not meta_file.exists():
            return metadata
        for line in meta_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator:
                metadata[key.strip()] = value.strip()
        return metadata
