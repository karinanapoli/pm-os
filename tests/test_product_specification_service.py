import json

import pytest

from pm_os.web.product_specification_service import (
    ProductSpecificationService,
    SPECIFICATION_FIELDS,
)


def _sections(**overrides):
    result = {field: "" for field in SPECIFICATION_FIELDS}
    result.update({
        "problem": "Checkout tem abandono elevado.",
        "users": "Clientes autenticados.",
        "evidence": "Pesquisa [SRC-12345678].",
        "outcome": "Reduzir esforço.",
        "metrics": "Conversão.",
        "scope": "Checkout autenticado.",
        "requirements": "- Reutilizar endereço\n- Confirmar pagamento",
        "risks": "Uso em dispositivo compartilhado.",
        "open_questions": "Qual a meta?",
        "acceptance_criteria": "- Endereço exige consentimento\n- Pagamento exige confirmação",
    })
    result.update(overrides)
    return result


def test_saves_versions_and_marks_derived_artifacts_stale(tmp_path):
    service = ProductSpecificationService()
    first = service.save(tmp_path, _sections(), actor="pm@example.com")
    service.approve(tmp_path, actor="pm@example.com")
    service.generate_backlog(tmp_path, actor="pm@example.com")

    second = service.save(
        tmp_path,
        _sections(problem="Checkout tem abandono elevado no mobile."),
        actor="pm@example.com",
    )

    assert first["version"] == 1
    assert second["version"] == 2
    assert second["status"] == "draft"
    assert second["artifacts"]["backlog"]["status"] == "stale"
    assert (tmp_path / "artifacts" / "history" / "specification-v001.json").exists()


def test_approval_and_backlog_keep_traceability(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, _sections(), source_ids=["SRC-12345678"])
    approved = service.approve(tmp_path, actor="pm@example.com")
    backlog = service.generate_backlog(tmp_path)

    assert approved["status"] == "approved"
    assert approved["approved_version"] == 1
    content = backlog.read_text(encoding="utf-8")
    assert content.startswith("## Iniciativa:")
    assert "## Épico:" in content
    assert "### História:" in content
    assert "US-001" in content
    assert "SPEC-v1" in content
    assert service.load(tmp_path)["artifacts"]["backlog"]["status"] == "current"


def test_backlog_accepts_structured_ai_markdown_and_removes_fence(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, _sections())
    service.approve(tmp_path)
    generated = """```markdown
## Iniciativa: Checkout

## Épico: Endereço salvo

### História: Reutilizar endereço
```"""

    backlog = service.generate_backlog(
        tmp_path,
        initiative_name="Checkout",
        generated_content=generated,
    )
    content = backlog.read_text(encoding="utf-8")

    assert content.startswith("## Iniciativa: Checkout")
    assert "```" not in content
    assert "SPEC-v1" in content


def test_backlog_context_contains_only_approved_specification(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, _sections())
    service.approve(tmp_path)

    context = json.loads(service.backlog_context(tmp_path, "Checkout"))

    assert context["initiative_name"] == "Checkout"
    assert context["specification_version"] == 1
    assert context["sections"]["requirements"].startswith("- Reutilizar")


def test_backlog_requires_approved_specification_and_requirements(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, _sections())
    with pytest.raises(ValueError, match="Approve"):
        service.generate_backlog(tmp_path)

    service.save(tmp_path, _sections(requirements=""))
    service.approve(tmp_path)
    with pytest.raises(ValueError, match="requirement"):
        service.generate_backlog(tmp_path)


def test_decision_is_persisted_without_overwriting_specification(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, _sections())
    decision = service.add_decision(
        tmp_path,
        title="Usar consentimento explícito",
        rationale="Reduz risco em dispositivos compartilhados.",
        actor="pm@example.com",
        source_ids=["SRC-12345678"],
        revisit_if="A adoção ficar abaixo de 30%.",
    )

    loaded = service.load(tmp_path)
    assert decision["id"] == "DEC-001"
    assert loaded["decisions"][0]["title"] == "Usar consentimento explícito"
    assert loaded["decisions"][0]["revisit_if"] == "A adoção ficar abaixo de 30%."
    assert loaded["decisions"][0]["status"] == "active"
    updated = service.update_decision_status(
        tmp_path,
        "DEC-001",
        status="revisited",
        actor="lead@example.com",
    )
    assert updated["status"] == "revisited"
    assert service.load(tmp_path)["decisions"][0]["updated_by"] == "lead@example.com"
    assert loaded["version"] == 1


def test_corrupt_state_falls_back_to_safe_empty_specification(tmp_path):
    path = tmp_path / "artifacts"
    path.mkdir()
    (path / "specification.json").write_text("{broken", encoding="utf-8")
    loaded = ProductSpecificationService().load(tmp_path)
    assert loaded["status"] == "not_started"
    assert loaded["version"] == 0


def test_atomic_json_contains_only_expected_sections(tmp_path):
    service = ProductSpecificationService()
    service.save(tmp_path, {**_sections(), "unexpected": "ignored"})
    raw = json.loads(
        (tmp_path / "artifacts" / "specification.json").read_text(encoding="utf-8")
    )
    assert "unexpected" not in raw["sections"]
    assert service.completion(raw) == 100


def test_quick_prd_bootstraps_editable_specification_only_once(tmp_path):
    service = ProductSpecificationService()
    prd = """# PRD

## Problema

Abandono no checkout.

## Objetivos

Reduzir esforço.

## Requisitos funcionais

- Reutilizar endereço.

## Métricas de sucesso

Conversão.
"""
    first = service.bootstrap_from_prd(
        tmp_path,
        prd,
        source_ids=["SRC-12345678"],
    )
    second = service.bootstrap_from_prd(
        tmp_path,
        prd.replace("Abandono", "Outro"),
    )

    assert first["version"] == 1
    assert first["sections"]["problem"] == "Abandono no checkout."
    assert first["sections"]["requirements"] == "- Reutilizar endereço."
    assert first["source_ids"] == ["SRC-12345678"]
    assert second["sections"]["problem"] == "Abandono no checkout."


def test_clarifications_expose_gaps_and_open_questions_without_blocking():
    service = ProductSpecificationService()
    specification = service._empty()
    specification["sections"]["problem"] = "Problema conhecido."
    specification["sections"]["open_questions"] = "- Qual é a meta?"

    clarifications = service.clarifications(specification)

    assert not any(item["field"] == "problem" for item in clarifications)
    assert any(item["field"] == "metrics" for item in clarifications)
    assert any(item["question"] == "Qual é a meta?" for item in clarifications)


def test_consistency_analysis_flags_traceability_acceptance_and_stale_artifacts():
    service = ProductSpecificationService()
    specification = service._empty()
    specification["sections"].update({
        "outcome": "Melhorar conversão.",
        "requirements": "- Um\n- Dois",
        "acceptance_criteria": "- Primeiro critério",
        "risks": "Dispositivo compartilhado.",
    })
    specification["artifacts"] = {"prd": {"status": "stale"}}

    findings = service.analyze(specification)
    messages = " ".join(item["message"] for item in findings)

    assert "fontes" in messages
    assert "métrica" in messages
    assert "critérios de aceite" in messages
    assert "mitigação" in messages
    assert "versão anterior" in messages


def test_ai_proposal_fills_blank_fields_and_preserves_pm_corrections(tmp_path):
    service = ProductSpecificationService()
    service.save(
        tmp_path,
        _sections(problem="Problema corrigido pela PM.", metrics=""),
    )
    proposal = json.dumps({
        "problem": "Problema sugerido pela IA.",
        "metrics": ["Conversão", "Tempo de checkout"],
        "open_questions": "Qual é a meta?",
    })

    result = service.prepare_from_generated(
        tmp_path,
        proposal,
        source_ids=["SRC-12345678"],
    )

    assert result["sections"]["problem"] == "Problema corrigido pela PM."
    assert result["sections"]["metrics"] == "- Conversão\n- Tempo de checkout"
    assert "metrics" in result["prepared_fields"]
    assert "problem" not in result["prepared_fields"]


def test_ai_proposal_accepts_fenced_json_and_demo_markdown(tmp_path):
    service = ProductSpecificationService()
    fenced = """```json
{"problem": "Problema da fonte.", "requirements": ["Um", "Dois"]}
```"""
    result = service.prepare_from_generated(tmp_path, fenced)
    assert result["sections"]["requirements"] == "- Um\n- Dois"

    other = tmp_path / "demo"
    demo = """# PRD
## Problema
Informações dispersas.
## Objetivos
Organizar contexto.
"""
    result = service.prepare_from_generated(other, demo)
    assert result["sections"]["problem"] == "Informações dispersas."
