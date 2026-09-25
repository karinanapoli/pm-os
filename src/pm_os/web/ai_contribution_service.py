"""File-backed external AI connection and proposal review state."""

from __future__ import annotations

import json
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


class AIContributionService:
    """Persist the Cursor prototype without granting direct specification writes."""

    def load(self, initiative_path: Path) -> dict:
        path = self._path(initiative_path)
        if not path.exists():
            return self._empty()
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._empty()
        state = self._empty()
        state.update({key: value for key, value in stored.items() if key in state})
        state["proposals"] = [
            item for item in (stored.get("proposals") or []) if isinstance(item, dict)
        ]
        return state

    def connect(self, initiative_path: Path, *, actor: str = "") -> dict:
        state = self.load(initiative_path)
        state.update({
            "connection_status": "connected",
            "connected_by": actor,
            "connected_at": self._now(),
        })
        self._persist(initiative_path, state)
        return state

    def share(self, initiative_path: Path, *, specification_version: int) -> dict:
        state = self.load(initiative_path)
        if state["connection_status"] != "connected":
            raise ValueError("Cursor must be connected before sharing an initiative.")
        state.update({
            "initiative_access": "shared",
            "shared_at": self._now(),
            "shared_specification_version": specification_version,
        })
        self._persist(initiative_path, state)
        return state

    def simulate(self, initiative_path: Path, *, specification_version: int) -> dict:
        state = self.load(initiative_path)
        if state["initiative_access"] != "shared":
            raise ValueError("The initiative must be shared before receiving proposals.")
        if not state["proposals"]:
            state["proposals"] = self._sample_proposals(specification_version)
            state["last_received_at"] = self._now()
            self._persist(initiative_path, state)
        return state

    def receive_proposals(
        self,
        initiative_path: Path,
        proposals: list[dict],
        *,
        specification_version: int,
        source: str,
    ) -> list[dict]:
        """Validate and append external proposals without applying them."""
        state = self.load(initiative_path)
        if state["initiative_access"] != "shared":
            raise ValueError("The initiative is not available to external agents.")
        accepted = []
        for raw in proposals:
            if not isinstance(raw, dict):
                raise ValueError("Each proposal must be an object.")
            field = str(raw.get("field") or "").strip()
            content = str(raw.get("content") or "").strip()
            reason = str(raw.get("reason") or "").strip()
            kind = str(raw.get("kind") or "").strip()
            if field not in {
                "evidence",
                "requirements",
                "open_questions",
                "acceptance_criteria",
                "risks",
                "dependencies",
            }:
                raise ValueError("Proposal field is not allowed.")
            if not content or not reason or not kind:
                raise ValueError("Proposal kind, content and reason are required.")
            item = {
                "id": f"EXT-{uuid.uuid4().hex[:12].upper()}",
                "field": field,
                "kind": kind,
                "content": content,
                "reason": reason,
                "status": "pending",
                "source": source.strip() or "external_agent",
                "specification_version": int(specification_version),
                "created_at": self._now(),
            }
            state["proposals"].append(item)
            accepted.append(deepcopy(item))
        if accepted:
            state["last_received_at"] = self._now()
            self._persist(initiative_path, state)
        return accepted

    def proposal_status(self, initiative_path: Path, proposal_ids: list[str]) -> list[dict]:
        """Return review status for proposals created by an external agent."""
        wanted = {str(item) for item in proposal_ids if str(item)}
        return [
            {
                "id": proposal.get("id", ""),
                "status": proposal.get("status", "pending"),
                "reviewed_at": proposal.get("reviewed_at", ""),
            }
            for proposal in self.load(initiative_path)["proposals"]
            if proposal.get("id") in wanted
        ]

    def decide(
        self,
        initiative_path: Path,
        proposal_id: str,
        *,
        decision: str,
        actor: str = "",
    ) -> dict:
        if decision not in {"approved", "rejected"}:
            raise ValueError("Invalid proposal decision.")
        state = self.load(initiative_path)
        for proposal in state["proposals"]:
            if proposal.get("id") != proposal_id:
                continue
            if proposal.get("status") != "pending":
                raise ValueError("Proposal has already been reviewed.")
            proposal.update({
                "status": decision,
                "reviewed_by": actor,
                "reviewed_at": self._now(),
            })
            self._persist(initiative_path, state)
            return deepcopy(proposal)
        raise ValueError("Proposal not found.")

    @staticmethod
    def pending(state: dict) -> list[dict]:
        return [item for item in state.get("proposals") or [] if item.get("status") == "pending"]

    @staticmethod
    def _sample_proposals(specification_version: int) -> list[dict]:
        return [
            {
                "id": "CURSOR-001",
                "field": "open_questions",
                "kind": "open_question",
                "content": "O usuário poderá retomar o fluxo do ponto em que parou?",
                "reason": "A implementação persiste estado parcial, mas a especificação não define a retomada.",
                "status": "pending",
                "source": "cursor",
                "specification_version": specification_version,
            },
            {
                "id": "CURSOR-002",
                "field": "open_questions",
                "kind": "open_question",
                "content": "Como o progresso deve ser calculado quando existem etapas condicionais?",
                "reason": "Foram identificados caminhos com quantidades diferentes de etapas.",
                "status": "pending",
                "source": "cursor",
                "specification_version": specification_version,
            },
            {
                "id": "CURSOR-003",
                "field": "acceptance_criteria",
                "kind": "acceptance_criterion",
                "content": "Ao avançar ou retornar uma etapa, o indicador deve refletir imediatamente a posição atual.",
                "reason": "Transforma o requisito de progresso em comportamento verificável.",
                "status": "pending",
                "source": "cursor",
                "specification_version": specification_version,
            },
        ]

    @staticmethod
    def _empty() -> dict:
        return {
            "connection_status": "disconnected",
            "connected_by": "",
            "connected_at": "",
            "initiative_access": "private",
            "shared_at": "",
            "shared_specification_version": 0,
            "last_received_at": "",
            "proposals": [],
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _path(initiative_path: Path) -> Path:
        return initiative_path / "artifacts" / "ai-contributions.json"

    def _persist(self, initiative_path: Path, state: dict) -> None:
        path = self._path(initiative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(path.parent),
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            temporary = Path(handle.name)
        temporary.replace(path)
