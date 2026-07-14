from dataclasses import dataclass, field


@dataclass
class SectionEvaluation:
    name: str
    score: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    rationale: str = ""
    action_items: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    overall_score: float
    summary: str
    sections: list[SectionEvaluation] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# PRD Validation Report",
            "",
            f"**Overall Score:** {self.overall_score:.1f}/10",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Section Breakdown",
            "",
        ]

        for section in self.sections:
            lines.append(f"### {section.name}")
            lines.append(f"**Score:** {section.score:.1f}/10")
            lines.append("")

            if section.rationale:
                lines.append(f"**Why this score:** {section.rationale}")
                lines.append("")

            if section.issues:
                lines.append("**Issues:**")
                for issue in section.issues:
                    lines.append(f"- {issue}")
                lines.append("")

            if section.action_items:
                lines.append("**Action items:**")
                for item in section.action_items:
                    lines.append(f"- [ ] {item}")
                lines.append("")

            if section.suggestions:
                lines.append("**Suggestions:**")
                for suggestion in section.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
