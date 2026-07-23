import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from pm_os.domain.initiative import Initiative
from pm_os.domain.context_source import CONFIDENTIALITY_LEVELS, ContextSource
from pm_os.infrastructure.utils import ALLOWED_EXTENSIONS, extract_pdf_text


class InitiativeRepository:
    """
    Loads product initiatives from the PM OS workspace.
    """

    def __init__(
        self,
        initiatives_path: str = "workspace/initiatives",
        squad_name: Optional[str] = None,
    ):
        self.initiatives_path = Path(initiatives_path)
        self.squad_name = squad_name

    def list_names(self) -> list[str]:
        """Returns initiative names without loading documents."""
        if not self.initiatives_path.exists():
            return []
        all_dirs = sorted(
            p.name for p in self.initiatives_path.iterdir()
            if p.is_dir()
        )
        if self.squad_name is None:
            return all_dirs
        return [name for name in all_dirs if self._get_squad(name) == self.squad_name]

    def list_initiatives(self) -> list[Initiative]:
        """
        Lists all initiatives available in the workspace.
        """

        if not self.initiatives_path.exists():
            return []

        initiatives: list[Initiative] = []

        for initiative_path in self.initiatives_path.iterdir():
            if not initiative_path.is_dir():
                continue
            init_squad = self._get_squad(initiative_path.name)
            if self.squad_name is None:
                pass  # no filter
            elif self.squad_name == "":
                if init_squad:
                    continue  # personal mode: skip squads
            else:
                if init_squad != self.squad_name:
                    continue

            context_path = initiative_path / "context"

            documents: list[str] = []
            sources: list[ContextSource] = []
            source_metadata = self._load_source_metadata(context_path)

            if context_path.exists():
                for document_path in sorted(context_path.iterdir()):
                    if (
                        document_path.is_file()
                        and not document_path.name.startswith(".")
                        and document_path.suffix in ALLOWED_EXTENSIONS
                    ):
                        if document_path.suffix == ".pdf":
                            content = extract_pdf_text(document_path)
                        else:
                            content = document_path.read_text(encoding="utf-8")
                        documents.append(content)
                        metadata = source_metadata.get(document_path.name, {})
                        confidentiality = metadata.get("confidentiality", "internal")
                        if confidentiality not in CONFIDENTIALITY_LEVELS:
                            confidentiality = "internal"
                        stat = document_path.stat()
                        sources.append(ContextSource(
                            source_id=self._source_id(initiative_path.name, document_path.name),
                            name=document_path.name,
                            content=content,
                            source_type=document_path.suffix.lstrip(".") or "text",
                            confidentiality=confidentiality,
                            author=str(metadata.get("author", "")),
                            modified_at=datetime.fromtimestamp(stat.st_mtime),
                            size_bytes=stat.st_size,
                        ))

            initiatives.append(
                Initiative(
                    name=initiative_path.name,
                    path=initiative_path,
                    documents=documents,
                    sources=sources,
                )
            )

        return initiatives

    @staticmethod
    def _source_id(initiative_name: str, filename: str) -> str:
        raw = f"{initiative_name}/{filename}".encode("utf-8")
        return f"SRC-{hashlib.sha256(raw).hexdigest()[:8].upper()}"

    @staticmethod
    def _load_source_metadata(context_path: Path) -> dict:
        metadata_path = context_path / ".sources.yaml"
        if not metadata_path.is_file():
            return {}
        try:
            data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            return data.get("sources", {}) if isinstance(data, dict) else {}
        except (OSError, yaml.YAMLError):
            return {}

    def _get_squad(self, name: str) -> str:
        path = self.initiatives_path / name / "metadata.yaml"
        if not path.exists():
            return ""
        try:
            with open(path, encoding="utf-8") as f:
                meta = yaml.safe_load(f)
            return meta.get("squad", "") if meta else ""
        except Exception:
            return ""
