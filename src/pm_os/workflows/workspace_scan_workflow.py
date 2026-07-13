from pathlib import Path
from typing import Optional

import yaml

from pm_os.contracts.logger import Logger
from pm_os.contracts.workflow_contracts import (
    InitiativeRepositoryProtocol,
)


class WorkspaceScanWorkflow:
    """
    Scans all initiatives and reports their current status.

    Shows: name, status, owner, PRD quality score, and alerts.
    """

    def __init__(
        self,
        initiative_repository: InitiativeRepositoryProtocol,
        logger: Logger,
    ):
        self.initiative_repository = initiative_repository
        self.logger = logger

    def run(self) -> str:
        self.logger.info("Scanning workspace for initiatives.")

        initiatives = self.initiative_repository.list_initiatives()

        if not initiatives:
            return "# Workspace Scan\n\nNo initiatives found."

        rows = []
        for initiative in initiatives:
            metadata = self._load_metadata(initiative.path)
            has_prd = (initiative.path / "artifacts" / "prd.md").exists()
            score = self._read_validation_score(initiative.path)
            status = metadata.get("status", "unknown") if metadata else "unknown"
            owner = metadata.get("owner", "-") if metadata else "-"

            score_str = f"{score}/10" if score is not None else "-"
            alert = self._determine_alert(score, status)
            rows.append((initiative.name, status, owner, score_str, alert))

        return self._format_report(rows)

    def _load_metadata(self, path: Path) -> Optional[dict]:
        metadata_path = path / "metadata.yaml"
        if metadata_path.exists():
            try:
                return yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                return None
        return None

    def _read_validation_score(self, path: Path) -> Optional[float]:
        report_path = path / "artifacts" / "prd-validation.md"
        if not report_path.exists():
            return None
        content = report_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "Overall Score:" in line:
                try:
                    score_str = line.split("**Overall Score:**")[-1].split("/")[0].strip()
                    return float(score_str)
                except (ValueError, IndexError):
                    return None
        return None

    def _determine_alert(self, score: Optional[float], status: str) -> str:
        if status == "discovery" and score is None:
            return "🟡"
        if score is not None and score < 5.0:
            return "🔴"
        if score is not None and score < 7.0:
            return "🟠"
        if score is not None:
            return "🟢"
        return "⚪"

    def _format_report(self, rows: list) -> str:
        lines = [
            "# Workspace Scan",
            "",
            "| Initiative | Status | Owner | PRD Score | Alert |",
            "|------------|--------|-------|-----------|-------|",
        ]

        for name, status, owner, score, alert in rows:
            lines.append(f"| {name} | {status} | {owner} | {score} | {alert} |")

        lines.append("")
        lines.append("**Legend:**")
        lines.append("- 🟢 Good (7+)")
        lines.append("- 🟠 Needs attention (5-7)")
        lines.append("- 🔴 Critical (< 5)")
        lines.append("- 🟡 In discovery")
        lines.append("- ⚪ No data")

        return "\n".join(lines)
