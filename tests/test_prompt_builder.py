from pm_os.prompt_builder import PromptBuilder


def test_prompt_builder_builds_create_prd_prompt():
    builder = PromptBuilder()

    prompt = builder.build(
        workflow_name="create_prd",
        context="Test context",
    )

    assert "Create a complete PRD" in prompt
    assert "Test context" in prompt
    assert "[SRC-XXXXXXXX]" in prompt
    assert "Source-backed facts" in prompt
    assert "Inferences" in prompt
    assert "Recommendations" in prompt
    assert "Do not cite, enumerate, or repeat every document" in prompt
    assert "Cite every factual claim" not in prompt


def test_prompt_builder_rejects_unknown_workflow():
    builder = PromptBuilder()

    try:
        builder.build(
            workflow_name="unknown_workflow",
            context="Context",
        )
    except ValueError as error:
        assert "Unsupported workflow" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_prompt_builder_creates_evidence_aware_product_specification_prompt():
    prompt = PromptBuilder().build(
        workflow_name="create_specification",
        context="Pesquisa [SRC-12345678]",
        lang="pt-BR",
    )

    assert "objeto JSON válido" in prompt
    assert "open_questions" in prompt
    assert "hypotheses" in prompt
    assert "Pesquisa [SRC-12345678]" in prompt


def test_prompt_builder_creates_hierarchical_backlog_prompt():
    prompt = PromptBuilder().build(
        workflow_name="create_backlog",
        context='{"initiative_name": "Checkout"}',
        lang="pt-BR",
    )

    assert "Iniciativa → Épico → História" in prompt
    assert "De 5 a 15 histórias independentes por épico" in prompt
    assert "3 a 5 critérios" in prompt
    assert "aceite" in prompt
    assert "## Iniciativa: [Nome]" in prompt
    assert "um único arquivo Markdown" in prompt
    assert "User Story" in prompt
    assert "Technical Story" in prompt
    assert "Job Story" in prompt
    assert "Technical Stories precisam declarar" in prompt
    assert "produto habilitado" in prompt
    assert "três dias de desenvolvimento" in prompt
    assert "3 a 5 critérios" in prompt
    assert '"initiative_name": "Checkout"' in prompt
