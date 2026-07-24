"""Deterministic verification of AI citations against supplied context sources."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SOURCE_BOUNDARY_RE = re.compile(r'<<<SOURCE\s+id="(SRC-[A-Z0-9]{8})"', re.IGNORECASE)
_CITATION_RE = re.compile(r"\[\s*(SRC-[A-Z0-9_-]+)\s*\]", re.IGNORECASE)


@dataclass(frozen=True)
class CitationReport:
    status: str
    available_ids: list[str]
    cited_ids: list[str]
    valid_ids: list[str]
    invalid_ids: list[str]
    missing_citations: bool


def extract_source_ids(context: str) -> set[str]:
    """Extract only source IDs declared by machine-readable context boundaries."""
    return {match.upper() for match in _SOURCE_BOUNDARY_RE.findall(context)}


def verify_citations(content: str, available_source_ids: set[str]) -> CitationReport:
    """Compare every citation-like source ID in AI output with supplied sources."""
    available = {source_id.upper() for source_id in available_source_ids}
    cited = {match.upper() for match in _CITATION_RE.findall(content)}
    valid = cited & available
    invalid = cited - available
    missing = bool(available) and not cited

    if not available:
        status = "not_applicable"
    elif invalid or missing:
        status = "needs_review"
    else:
        status = "verified"

    return CitationReport(
        status=status,
        available_ids=sorted(available),
        cited_ids=sorted(cited),
        valid_ids=sorted(valid),
        invalid_ids=sorted(invalid),
        missing_citations=missing,
    )
