"""Application service behind the local PM Studio MCP server for Cursor."""

from __future__ import annotations

import os
from pathlib import Path

from pm_os.context_builder import ContextBuilder
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.web.ai_contribution_service import AIContributionService
from pm_os.web.product_specification_service import ProductSpecificationService


class CursorMCPService:
    """Expose explicitly shared initiatives to an external local agent."""

    def __init__(self, workspace_dir: Path | str | None = None):
        configured = workspace_dir or os.getenv("PM_OS_WORKSPACE_DIR", "workspace")
        self.workspace_dir = Path(configured).expanduser().resolve()
        self.repository = InitiativeRepository(
            initiatives_path=str(self.workspace_dir / "initiatives")
        )
        self.context_builder = ContextBuilder()
        self.specifications = ProductSpecificationService()
        self.contributions = AIContributionService()

    def list_initiatives(self) -> list[dict]:
        result = []
        for name in self.repository.list_names():
            initiative = self.repository.get(name, load_content=False)
            if not initiative or not self._is_shared(initiative.path):
                continue
            specification = self.specifications.load(initiative.path)
            result.append({
                "id": initiative.name,
                "title": self._display_name(initiative.path, initiative.name),
                "specification_version": int(specification.get("version") or 0),
                "specification_status": str(specification.get("status") or "not_started"),
            })
        return result

    def get_initiative_context(self, initiative_name: str) -> dict:
        initiative = self._shared_initiative(initiative_name, load_content=True)
        specification = self.specifications.load(initiative.path)
        return {
            "initiative_id": initiative.name,
            "title": self._display_name(initiative.path, initiative.name),
            "context": self.context_builder.build(initiative),
            "specification": specification,
        }

    def get_specification(self, initiative_name: str) -> dict:
        initiative = self._shared_initiative(initiative_name, load_content=False)
        return self.specifications.load(initiative.path)

    def get_prd(self, initiative_name: str) -> str:
        initiative = self._shared_initiative(initiative_name, load_content=False)
        path = initiative.path / "artifacts" / "prd.md"
        if not path.is_file():
            raise ValueError(f"PRD for initiative '{initiative_name}' not found.")
        return path.read_text(encoding="utf-8")

    def add_technical_discovery(
        self,
        initiative_name: str,
        *,
        summary: str,
        reason: str,
        specification_version: int,
        references: list[str] | None = None,
    ) -> dict:
        initiative = self._shared_initiative(initiative_name, load_content=False)
        reference_text = ", ".join(str(item) for item in (references or []) if str(item).strip())
        content = summary.strip()
        if reference_text:
            content += f"\nReferências técnicas: {reference_text}"
        received = self.contributions.receive_proposals(
            initiative.path,
            [{
                "field": "evidence",
                "kind": "technical_discovery",
                "content": content,
                "reason": reason,
            }],
            specification_version=specification_version,
            source="cursor",
        )
        return received[0]

    def propose_changes(
        self,
        initiative_name: str,
        *,
        proposals: list[dict],
        specification_version: int,
    ) -> dict:
        initiative = self._shared_initiative(initiative_name, load_content=False)
        current = self.specifications.load(initiative.path)
        accepted = self.contributions.receive_proposals(
            initiative.path,
            proposals,
            specification_version=specification_version,
            source="cursor",
        )
        return {
            "proposal_ids": [item["id"] for item in accepted],
            "status": "pending_review",
            "based_on_version": specification_version,
            "current_version": int(current.get("version") or 0),
            "stale": specification_version != int(current.get("version") or 0),
        }

    def get_proposal_status(self, initiative_name: str, proposal_ids: list[str]) -> list[dict]:
        initiative = self._shared_initiative(initiative_name, load_content=False)
        return self.contributions.proposal_status(initiative.path, proposal_ids)

    def _shared_initiative(self, name: str, *, load_content: bool):
        initiative = self.repository.get(name, load_content=load_content)
        if not initiative or not self._is_shared(initiative.path):
            raise ValueError("Initiative not found or not shared with external agents.")
        return initiative

    def _is_shared(self, initiative_path: Path) -> bool:
        state = self.contributions.load(initiative_path)
        return state.get("initiative_access") == "shared"

    @staticmethod
    def _display_name(initiative_path: Path, fallback: str) -> str:
        metadata_path = initiative_path / "metadata.yaml"
        if not metadata_path.is_file():
            return fallback
        try:
            import yaml

            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            return str(metadata.get("name") or fallback)
        except (OSError, yaml.YAMLError):
            return fallback
