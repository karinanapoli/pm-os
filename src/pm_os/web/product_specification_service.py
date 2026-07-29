"""File-backed product specification lifecycle for an initiative."""

from __future__ import annotations

import json
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


SPECIFICATION_FIELDS = (
    "problem",
    "users",
    "evidence",
    "outcome",
    "metrics",
    "scope",
    "out_of_scope",
    "requirements",
    "constraints",
    "risks",
    "dependencies",
    "hypotheses",
    "open_questions",
    "acceptance_criteria",
)


class ProductSpecificationService:
    """Persist specifications, approvals, decisions and derived artifacts."""

    def load(self, initiative_path: Path) -> dict:
        path = self._state_path(initiative_path)
        if not path.exists():
            return self._empty()
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._empty()
        specification = self._empty()
        specification.update({
            key: value
            for key, value in stored.items()
            if key in specification
        })
        specification["sections"] = {
            field: str((stored.get("sections") or {}).get(field, ""))
            for field in SPECIFICATION_FIELDS
        }
        specification["decisions"] = []
        for stored_decision in stored.get("decisions") or []:
            if not isinstance(stored_decision, dict):
                continue
            item = deepcopy(stored_decision)
            item.setdefault("status", "active")
            item.setdefault("revisit_if", "")
            item.setdefault("updated_at", item.get("created_at", ""))
            item.setdefault("updated_by", item.get("created_by", ""))
            specification["decisions"].append(item)
        specification["artifacts"] = stored.get("artifacts") or {}
        return specification

    def save(
        self,
        initiative_path: Path,
        sections: dict,
        *,
        source_ids: Optional[Iterable[str]] = None,
        actor: str = "",
    ) -> dict:
        current = self.load(initiative_path)
        normalized = {
            field: str(sections.get(field, "")).strip()
            for field in SPECIFICATION_FIELDS
        }
        if normalized == current["sections"] and current["version"] > 0:
            return current

        now = self._now()
        version = int(current.get("version") or 0) + 1
        updated = deepcopy(current)
        updated.update({
            "version": version,
            "status": "draft",
            "sections": normalized,
            "source_ids": sorted({
                item.strip()
                for item in (source_ids or current.get("source_ids") or [])
                if item and item.strip()
            }),
            "updated_at": now,
            "updated_by": actor,
            "approved_version": None,
            "approved_at": "",
            "approved_by": "",
        })
        updated["artifacts"] = self._mark_derived_stale(
            current.get("artifacts") or {},
            version,
        )
        self._archive(initiative_path, current)
        self._persist(initiative_path, updated)
        self._write_markdown(initiative_path, updated)
        return updated

    def approve(self, initiative_path: Path, *, actor: str = "") -> dict:
        current = self.load(initiative_path)
        if not current.get("version"):
            raise ValueError("A specification must be saved before approval.")
        current.update({
            "status": "approved",
            "approved_version": current["version"],
            "approved_at": self._now(),
            "approved_by": actor,
            "updated_at": self._now(),
        })
        self._persist(initiative_path, current)
        self._write_markdown(initiative_path, current)
        return current

    def add_decision(
        self,
        initiative_path: Path,
        *,
        title: str,
        rationale: str,
        actor: str = "",
        source_ids: Optional[Iterable[str]] = None,
        revisit_if: str = "",
    ) -> dict:
        title = title.strip()
        rationale = rationale.strip()
        if not title or not rationale:
            raise ValueError("Decision title and rationale are required.")
        current = self.load(initiative_path)
        decision = {
            "id": f"DEC-{len(current['decisions']) + 1:03d}",
            "title": title,
            "rationale": rationale,
            "source_ids": sorted({
                item.strip()
                for item in (source_ids or [])
                if item and item.strip()
            }),
            "created_at": self._now(),
            "created_by": actor,
            "revisit_if": revisit_if.strip(),
            "status": "active",
            "updated_at": self._now(),
            "updated_by": actor,
        }
        current["decisions"].append(decision)
        current["updated_at"] = self._now()
        self._persist(initiative_path, current)
        return decision

    def update_decision_status(
        self,
        initiative_path: Path,
        decision_id: str,
        *,
        status: str,
        actor: str = "",
    ) -> Optional[dict]:
        if status not in {"active", "revisited", "superseded"}:
            raise ValueError("Invalid decision status.")
        current = self.load(initiative_path)
        for decision in current["decisions"]:
            if decision.get("id") != decision_id:
                continue
            decision["status"] = status
            decision["updated_at"] = self._now()
            decision["updated_by"] = actor
            current["updated_at"] = self._now()
            self._persist(initiative_path, current)
            return decision
        return None

    def generate_backlog(self, initiative_path: Path, *, actor: str = "") -> Path:
        current = self.load(initiative_path)
        if current.get("status") != "approved":
            raise ValueError("Approve the specification before generating a backlog.")

        requirements = self._items(current["sections"].get("requirements", ""))
        acceptance = self._items(current["sections"].get("acceptance_criteria", ""))
        if not requirements:
            raise ValueError("Add at least one requirement before generating a backlog.")

        lines = [
            "# Backlog",
            "",
            f"> Derivado da Especificação v{current['version']}.",
            "",
        ]
        for index, requirement in enumerate(requirements, start=1):
            criteria = acceptance[index - 1] if index <= len(acceptance) else (
                "Critérios de aceite devem ser refinados com o time."
            )
            lines.extend([
                f"## US-{index:03d} — {requirement}",
                "",
                f"**Objetivo:** {requirement}",
                "",
                "**Critérios de aceite:**",
                f"- {criteria}",
                "",
                f"**Rastreabilidade:** SPEC-v{current['version']}",
                "",
            ])

        artifacts = initiative_path / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        output = artifacts / "backlog.md"
        self._version_existing(output)
        output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        current["artifacts"]["backlog"] = {
            "path": "artifacts/backlog.md",
            "derived_from_version": current["version"],
            "status": "current",
            "generated_at": self._now(),
            "generated_by": actor,
        }
        self._persist(initiative_path, current)
        return output

    def register_prd(self, initiative_path: Path, *, actor: str = "") -> None:
        current = self.load(initiative_path)
        if not current.get("version"):
            return
        current["artifacts"]["prd"] = {
            "path": "artifacts/prd.md",
            "derived_from_version": current["version"],
            "status": "current",
            "generated_at": self._now(),
            "generated_by": actor,
        }
        self._persist(initiative_path, current)

    def bootstrap_from_prd(
        self,
        initiative_path: Path,
        prd_content: str,
        *,
        source_ids: Optional[Iterable[str]] = None,
        actor: str = "",
    ) -> dict:
        """Create a first editable specification behind the quick PRD flow."""
        current = self.load(initiative_path)
        if current.get("version"):
            return current
        sections = self._sections_from_markdown(prd_content)
        return self.save(
            initiative_path,
            sections,
            source_ids=source_ids,
            actor=actor,
        )

    def prepare_from_generated(
        self,
        initiative_path: Path,
        generated_content: str,
        *,
        source_ids: Optional[Iterable[str]] = None,
        actor: str = "",
        replace_existing: bool = False,
    ) -> dict:
        """Merge an AI proposal into blank fields, preserving PM corrections."""
        proposed = self._parse_generated_sections(generated_content)
        current = self.load(initiative_path)
        merged = {}
        for field in SPECIFICATION_FIELDS:
            existing = str(current["sections"].get(field, "")).strip()
            candidate = str(proposed.get(field, "")).strip()
            merged[field] = candidate if replace_existing or not existing else existing
        result = self.save(
            initiative_path,
            merged,
            source_ids=source_ids,
            actor=actor,
        )
        result["prepared_fields"] = [
            field for field in SPECIFICATION_FIELDS
            if proposed.get(field) and (replace_existing or not current["sections"].get(field))
        ]
        return result

    def _parse_generated_sections(self, content: str) -> dict:
        candidate = content.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return self._sections_from_markdown(content)
        if not isinstance(parsed, dict):
            return {field: "" for field in SPECIFICATION_FIELDS}
        return {
            field: self._string_value(parsed.get(field, ""))
            for field in SPECIFICATION_FIELDS
        }

    @staticmethod
    def _string_value(value: object) -> str:
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value if str(item).strip())
        if isinstance(value, (str, int, float, bool)):
            return str(value).strip()
        return ""

    def _sections_from_markdown(self, content: str) -> dict:
        headings = self._markdown_sections(content)
        aliases = {
            "problem": ("problema", "problem"),
            "users": ("personas / usuários", "personas", "usuários", "users"),
            "outcome": ("objetivos", "objectives", "goals"),
            "metrics": ("métricas de sucesso", "success metrics"),
            "scope": ("escopo", "scope"),
            "out_of_scope": ("fora do escopo", "out of scope"),
            "requirements": (
                "requisitos funcionais", "functional requirements",
                "requisitos", "requirements",
            ),
            "constraints": (
                "requisitos não funcionais", "non-functional requirements",
                "restrições", "constraints",
            ),
            "risks": ("riscos", "risks"),
            "hypotheses": ("inferências", "inferences"),
            "open_questions": ("perguntas em aberto", "open questions"),
        }
        sections = {field: "" for field in SPECIFICATION_FIELDS}
        for field, candidates in aliases.items():
            sections[field] = next(
                (headings[candidate] for candidate in candidates if headings.get(candidate)),
                "",
            )
        sections["evidence"] = next(
            (
                content for heading, content in headings.items()
                if "fatos" in heading or "source-backed" in heading
            ),
            "",
        )
        return sections

    def completion(self, specification: dict) -> int:
        sections = specification.get("sections") or {}
        weighted = (
            "problem", "users", "evidence", "outcome", "metrics", "scope",
            "requirements", "risks", "open_questions", "acceptance_criteria",
        )
        completed = sum(bool(str(sections.get(field, "")).strip()) for field in weighted)
        return round(completed / len(weighted) * 100)

    def clarifications(self, specification: dict, lang: str = "pt-BR") -> list[dict]:
        sections = specification.get("sections") or {}
        prompts = {
            "pt-BR": {
                "problem": "Qual problema existe, para quem e com qual evidência?",
                "outcome": "Qual comportamento ou resultado deve mudar?",
                "metrics": "Como saberemos que a iniciativa funcionou?",
                "scope": "O que faz parte desta entrega e o que ficará de fora?",
                "requirements": "Quais capacidades mínimas precisam ser entregues?",
                "risks": "Qual é o principal risco e como ele pode ser mitigado?",
                "acceptance_criteria": "Como o time verificará que os requisitos foram atendidos?",
            },
            "en": {
                "problem": "What problem exists, for whom, and with what evidence?",
                "outcome": "Which behavior or outcome should change?",
                "metrics": "How will we know the initiative worked?",
                "scope": "What is part of this delivery and what is out of scope?",
                "requirements": "Which minimum capabilities must be delivered?",
                "risks": "What is the main risk and how can it be mitigated?",
                "acceptance_criteria": "How will the team verify requirements were met?",
            },
        }
        selected = prompts["en" if lang == "en" else "pt-BR"]
        result = [
            {"field": field, "question": question, "kind": "gap"}
            for field, question in selected.items()
            if not str(sections.get(field, "")).strip()
        ]
        result.extend({
            "field": "open_questions",
            "question": item,
            "kind": "open",
        } for item in self._items(str(sections.get("open_questions", ""))))
        return result

    def analyze(self, specification: dict, lang: str = "pt-BR") -> list[dict]:
        sections = specification.get("sections") or {}
        messages = {
            "pt-BR": {
                "evidence": "A especificação ainda não está vinculada a fontes.",
                "metrics": "O resultado esperado ainda não possui uma métrica.",
                "acceptance": "Há mais requisitos do que critérios de aceite.",
                "risk": "Os riscos não apresentam uma mitigação explícita.",
                "stale": "Há entregáveis derivados de uma versão anterior.",
            },
            "en": {
                "evidence": "The specification is not linked to sources yet.",
                "metrics": "The expected outcome does not have a metric yet.",
                "acceptance": "There are more requirements than acceptance criteria.",
                "risk": "Risks do not include an explicit mitigation.",
                "stale": "Some deliverables were derived from an older version.",
            },
        }
        text = messages["en" if lang == "en" else "pt-BR"]
        findings = []
        if not specification.get("source_ids") and not sections.get("evidence", "").strip():
            findings.append({"kind": "warning", "message": text["evidence"]})
        if sections.get("outcome", "").strip() and not sections.get("metrics", "").strip():
            findings.append({"kind": "warning", "message": text["metrics"]})
        requirements = self._items(sections.get("requirements", ""))
        criteria = self._items(sections.get("acceptance_criteria", ""))
        if requirements and len(criteria) < len(requirements):
            findings.append({"kind": "warning", "message": text["acceptance"]})
        risks = sections.get("risks", "").casefold()
        mitigation_words = ("mitiga", "reduz", "evitar", "monitor", "mitigat", "reduce")
        if risks and not any(word in risks for word in mitigation_words):
            findings.append({"kind": "info", "message": text["risk"]})
        if any(
            item.get("status") == "stale"
            for item in (specification.get("artifacts") or {}).values()
        ):
            findings.append({"kind": "warning", "message": text["stale"]})
        return findings

    def history(self, initiative_path: Path) -> list[dict]:
        history_dir = self._history_dir(initiative_path)
        if not history_dir.exists():
            return []
        result = []
        for path in sorted(history_dir.glob("specification-v*.json"), reverse=True):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            result.append({
                "version": item.get("version", 0),
                "status": item.get("status", "draft"),
                "updated_at": item.get("updated_at", ""),
            })
        return result

    @staticmethod
    def _empty() -> dict:
        return {
            "version": 0,
            "status": "not_started",
            "sections": {field: "" for field in SPECIFICATION_FIELDS},
            "source_ids": [],
            "decisions": [],
            "artifacts": {},
            "updated_at": "",
            "updated_by": "",
            "approved_version": None,
            "approved_at": "",
            "approved_by": "",
        }

    @staticmethod
    def _items(value: str) -> list[str]:
        result = []
        for line in value.splitlines():
            item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if item:
                result.append(item)
        return result

    @staticmethod
    def _markdown_sections(content: str) -> dict[str, str]:
        result: dict[str, list[str]] = {}
        current = ""
        for line in content.splitlines():
            match = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
            if match:
                current = match.group(1).strip().casefold()
                result.setdefault(current, [])
            elif current:
                result[current].append(line)
        return {
            heading: "\n".join(lines).strip()
            for heading, lines in result.items()
        }

    @staticmethod
    def _mark_derived_stale(artifacts: dict, version: int) -> dict:
        result = deepcopy(artifacts)
        for artifact in result.values():
            if int(artifact.get("derived_from_version") or 0) < version:
                artifact["status"] = "stale"
        return result

    def _archive(self, initiative_path: Path, current: dict) -> None:
        if not current.get("version"):
            return
        history = self._history_dir(initiative_path)
        history.mkdir(parents=True, exist_ok=True)
        path = history / f"specification-v{current['version']:03d}.json"
        if not path.exists():
            path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _persist(self, initiative_path: Path, data: dict) -> None:
        path = self._state_path(initiative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        ) as temporary:
            json.dump(data, temporary, ensure_ascii=False, indent=2)
            temporary.flush()
            temp_path = Path(temporary.name)
        temp_path.replace(path)

    def _write_markdown(self, initiative_path: Path, specification: dict) -> None:
        labels = {
            "problem": "Problema",
            "users": "Pessoas usuárias",
            "evidence": "Evidências",
            "outcome": "Resultado esperado",
            "metrics": "Métricas de sucesso",
            "scope": "Escopo",
            "out_of_scope": "Fora do escopo",
            "requirements": "Requisitos",
            "constraints": "Restrições",
            "risks": "Riscos",
            "dependencies": "Dependências",
            "hypotheses": "Hipóteses",
            "open_questions": "Perguntas em aberto",
            "acceptance_criteria": "Critérios de aceite",
        }
        lines = [
            "# Especificação de Produto",
            "",
            f"> Versão {specification['version']} · {specification['status']}",
            "",
        ]
        for field in SPECIFICATION_FIELDS:
            lines.extend([
                f"## {labels[field]}",
                "",
                specification["sections"].get(field, "") or "_Não informado._",
                "",
            ])
        if specification.get("source_ids"):
            lines.extend([
                "## Fontes relacionadas",
                "",
                ", ".join(f"[{item}]" for item in specification["source_ids"]),
                "",
            ])
        path = initiative_path / "artifacts" / "specification.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    @staticmethod
    def _version_existing(path: Path) -> None:
        if not path.exists():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path.replace(path.with_name(f"{path.stem}-{timestamp}{path.suffix}"))

    @staticmethod
    def _state_path(initiative_path: Path) -> Path:
        return initiative_path / "artifacts" / "specification.json"

    @staticmethod
    def _history_dir(initiative_path: Path) -> Path:
        return initiative_path / "artifacts" / "history"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
