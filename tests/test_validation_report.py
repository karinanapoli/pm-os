from pm_os.domain.validation_report import ValidationReport, SectionEvaluation


def test_to_markdown_en():
    report = ValidationReport(
        overall_score=7.5,
        summary="Good PRD.",
        sections=[
            SectionEvaluation(
                name="Metrics",
                score=8.0,
                rationale="Clear metrics.",
                issues=["Missing baseline"],
                action_items=["Define baseline"],
                suggestions=["Add more KPIs"],
            ),
        ],
    )
    md = report.to_markdown(lang="en")
    assert "# PRD Validation Report" in md
    assert "**Overall Score:** 7.5/10" in md
    assert "## Summary" in md
    assert "Good PRD." in md
    assert "## Section Breakdown" in md
    assert "### Metrics" in md
    assert "**Score:** 8.0/10" in md
    assert "**Why this score:** Clear metrics." in md
    assert "**Issues:**" in md
    assert "- Missing baseline" in md
    assert "**Action items:**" in md
    assert "- [ ] Define baseline" in md
    assert "**Suggestions:**" in md
    assert "- Add more KPIs" in md


def test_to_markdown_ptbr():
    report = ValidationReport(
        overall_score=7.5,
        summary="Bom PRD.",
        sections=[
            SectionEvaluation(
                name="Métricas",
                score=8.0,
                rationale="Métricas claras.",
                issues=["Falta baseline"],
                action_items=["Definir baseline"],
                suggestions=["Adicionar mais KPIs"],
            ),
        ],
    )
    md = report.to_markdown(lang="pt-BR")
    assert "Relatório de Validação de PRD" in md
    assert "**Nota Geral:** 7.5/10" in md
    assert "## Resumo" in md
    assert "Bom PRD." in md
    assert "## Detalhamento por Seção" in md
    assert "### Métricas" in md
    assert "**Por que esta nota:** Métricas claras." in md
    assert "**Problemas:**" in md
    assert "- Falta baseline" in md
    assert "**Ações necessárias:**" in md
    assert "- [ ] Definir baseline" in md
    assert "**Sugestões:**" in md
    assert "- Adicionar mais KPIs" in md


def test_to_markdown_empty_values():
    report = ValidationReport(
        overall_score=0.0,
        summary="",
        sections=[],
    )
    md = report.to_markdown(lang="en")
    assert "PRD Validation Report" in md
    assert "0.0/10" in md
    assert "## Section Breakdown" in md


def test_to_markdown_default_lang():
    report = ValidationReport(overall_score=8.0, summary="Great.")
    md = report.to_markdown()
    assert "PRD Validation Report" in md
    assert "**Overall Score:**" in md
