"""Data shapes shared by the insight agents, the orchestrator and the store."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass
class Evidence:
    source_id: str
    source_name: str
    excerpt: str


@dataclass
class Insight:
    """A reviewable finding produced by one agent, always backed by evidence."""

    agent: str
    kind: str
    key: str
    title: str
    summary: str
    evidence: list[Evidence]
    confidence: float
    impact: float
    signal_type: str
    implication: str = ""
    recommendation: str = ""
    synthesized: bool = False
    status: str = "new"
    signal_id: str = ""
    id: str = ""

    @property
    def fingerprint(self) -> str:
        return f"{self.agent}:{self.kind}:{self.key}"

    @property
    def score(self) -> float:
        return round(self.impact * self.confidence, 4)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["fingerprint"] = self.fingerprint
        data["score"] = self.score
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Insight":
        evidence = [Evidence(**item) for item in data.get("evidence") or [] if isinstance(item, dict)]
        allowed = {name for name in cls.__dataclass_fields__ if name != "evidence"}
        values = {key: value for key, value in data.items() if key in allowed}
        return cls(evidence=evidence, **values)


@dataclass
class SourceDocument:
    source_id: str
    name: str
    content: str


@dataclass
class Spreadsheet:
    name: str
    rows: list[dict[str, str]]


@dataclass
class InsightContext:
    """Everything the agents may read about one initiative. Agents never fetch on their own."""

    initiative: str
    lang: str = "pt-BR"
    spreadsheets: list[Spreadsheet] = field(default_factory=list)
    documents: list[SourceDocument] = field(default_factory=list)
    specification: dict[str, str] = field(default_factory=dict)
    automations: list[dict] = field(default_factory=list)


class InsightAgent(Protocol):
    name: str

    def analyze(self, context: InsightContext, prior: list[Insight]) -> list[Insight]:
        """Return new insights; ``prior`` holds what earlier agents already found."""


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str: ...

