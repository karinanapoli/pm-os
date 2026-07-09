from pm_os.prompt_builder import PromptBuilder


def test_prompt_builder_builds_create_prd_prompt():
    builder = PromptBuilder()

    prompt = builder.build(
        workflow_name="create_prd",
        context="Contexto de teste",
    )

    assert "Crie um PRD completo" in prompt
    assert "Contexto de teste" in prompt


def test_prompt_builder_rejects_unknown_workflow():
    builder = PromptBuilder()

    try:
        builder.build(
            workflow_name="unknown_workflow",
            context="Contexto",
        )
    except ValueError as error:
        assert "Unsupported workflow" in str(error)
    else:
        raise AssertionError("Expected ValueError")