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

    def to_markdown(self, lang: str = "en") -> str:
        if lang == "pt-BR":
            title = "Relatório de Validação de PRD"
            score_label = "**Nota Geral:**"
            summary_label = "## Resumo"
            breakdown_label = "## Detalhamento por Seção"
            rationale_label = "**Por que esta nota:**"
            issues_label = "**Problemas:**"
            action_label = "**Ações necessárias:**"
            suggestions_label = "**Sugestões:**"
        else:
            title = "PRD Validation Report"
            score_label = "**Overall Score:**"
            summary_label = "## Summary"
            breakdown_label = "## Section Breakdown"
            rationale_label = "**Why this score:**"
            issues_label = "**Issues:**"
            action_label = "**Action items:**"
            suggestions_label = "**Suggestions:**"

        lines = [
            f"# {title}",
            "",
            f"{score_label} {self.overall_score:.1f}/10",
            "",
            summary_label,
            "",
            self.summary,
            "",
            breakdown_label,
            "",
        ]

        for section in self.sections:
            lines.append(f"### {section.name}")
            lines.append(f"**Score:** {section.score:.1f}/10")
            lines.append("")

            if section.rationale:
                lines.append(f"{rationale_label} {section.rationale}")
                lines.append("")

            if section.issues:
                lines.append(f"{issues_label}")
                for issue in section.issues:
                    lines.append(f"- {issue}")
                lines.append("")

            if section.action_items:
                lines.append(f"{action_label}")
                for item in section.action_items:
                    lines.append(f"- [ ] {item}")
                lines.append("")

            if section.suggestions:
                lines.append(f"{suggestions_label}")
                for suggestion in section.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
