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
