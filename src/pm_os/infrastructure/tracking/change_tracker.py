import hashlib
import json
from pathlib import Path


class ChangeTracker:
    """
    Tracks changes in initiative context files.

    Stores file hashes in a manifest to detect what changed
    between workflow executions.
    """

    def __init__(self, initiatives_path: str = "workspace/initiatives"):
        self.initiatives_path = Path(initiatives_path)

    def detect_changes(self, initiative_path: str) -> list[dict]:
        initiative_path = Path(initiative_path)
        manifest = self._load_manifest(initiative_path)
        current_files = self._scan_files(initiative_path)

        changes = []
        for rel_path, current_hash in current_files.items():
            previous_hash = manifest.get(rel_path)
            if previous_hash is None:
                changes.append({"file": rel_path, "change": "added"})
            elif previous_hash != current_hash:
                changes.append({"file": rel_path, "change": "modified"})

        for rel_path in manifest:
            if rel_path not in current_files:
                changes.append({"file": rel_path, "change": "removed"})

        return changes

    def update_manifest(self, initiative_path: str) -> None:
        initiative_path = Path(initiative_path)
        current_files = self._scan_files(initiative_path)
        manifest_path = initiative_path / ".context_manifest.json"
        manifest_path.write_text(
            json.dumps(current_files, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_manifest(self, initiative_path: Path) -> dict:
        manifest_path = initiative_path / ".context_manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        return {}

    def _scan_files(self, initiative_path: Path) -> dict:
        files = {}
        for file_path in initiative_path.rglob("*"):
            if file_path.is_file() and file_path.name != ".context_manifest.json":
                rel_path = str(file_path.relative_to(initiative_path))
                files[rel_path] = self._hash_file(file_path)
        return files

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
