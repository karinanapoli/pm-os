"""Orchestrates the insight agents and persists reviewable results per initiative."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from pm_os.insights.agents import DEFAULT_AGENTS, SynthesisAgent
from pm_os.insights.models import Insight, InsightAgent, InsightContext, TextGenerator


class InsightEngine:
    """Runs each agent in order (later agents see earlier findings), then ranks the result."""

    def __init__(self, agents: Iterable[InsightAgent] = DEFAULT_AGENTS, synthesizer: Optional[TextGenerator] = None):
        self.agents = list(agents)
        self.synthesizer = synthesizer

    def run(self, context: InsightContext) -> list[Insight]:
        found: list[Insight] = []
        for agent in self.agents:
            found.extend(agent.analyze(context, list(found)))
        unique: dict[str, Insight] = {}
        for insight in found:
            key = re.sub(r"\W+", " ", insight.title.lower()).strip()
            if key not in unique or unique[key].score < insight.score:
                unique[key] = insight
        ranked = sorted(unique.values(), key=lambda item: item.score, reverse=True)
        if self.synthesizer is not None:
            ranked = SynthesisAgent(self.synthesizer).refine(ranked, context.lang)
        for insight in ranked:
            insight.id = "INS-" + hashlib.sha1(insight.fingerprint.encode("utf-8")).hexdigest()[:8]
        return ranked


class InsightStore:
    """``data-sources/insights.json``: latest run plus the PM's decisions on each finding."""

    filename = "insights.json"

    def _path(self, initiative_path: Path) -> Path:
        return initiative_path / "data-sources" / self.filename

    def load(self, initiative_path: Path) -> dict:
        path = self._path(initiative_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except (OSError, json.JSONDecodeError):
            data = {}
        insights = [Insight.from_dict(item) for item in data.get("insights") or [] if isinstance(item, dict)]
        return {
            "generated_at": data.get("generated_at", ""),
            "agents": data.get("agents") or [],
            "synthesized": bool(data.get("synthesized")),
            "insights": insights,
        }

    def save_run(self, initiative_path: Path, insights: list[Insight], *, agents: list[str], synthesized: bool) -> dict:
        previous = {item.fingerprint: item for item in self.load(initiative_path)["insights"]}
        for insight in insights:
            earlier = previous.get(insight.fingerprint)
            if earlier and earlier.status != "new":
                insight.status, insight.signal_id = earlier.status, earlier.signal_id
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agents": agents,
            "synthesized": synthesized,
            "insights": [item.to_dict() for item in insights],
        }
        self._write(initiative_path, payload)
        return self.load(initiative_path)

    def set_status(self, initiative_path: Path, insight_id: str, status: str, signal_id: str = "") -> Optional[Insight]:
        current = self.load(initiative_path)
        target = next((item for item in current["insights"] if item.id == insight_id), None)
        if target is None:
            return None
        target.status = status
        target.signal_id = signal_id or target.signal_id
        self._write(initiative_path, {
            "generated_at": current["generated_at"],
            "agents": current["agents"],
            "synthesized": current["synthesized"],
            "insights": [item.to_dict() for item in current["insights"]],
        })
        return target

    def _write(self, initiative_path: Path, payload: dict) -> None:
        path = self._path(initiative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
