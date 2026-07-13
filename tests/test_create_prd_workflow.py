from pathlib import Path

from pm_os.domain.validation_report import ValidationReport
from pm_os.workflows.create_prd_workflow import CreatePRDWorkflow


class FakeRepository:
    def __init__(self, initiatives):
        self._initiatives = initiatives

    def list_initiatives(self):
        return self._initiatives


class FakeInitiative:
    def __init__(self, name, documents):
        self.name = name
        self.documents = documents


class FakeContextBuilder:
    def build(self, initiative):
        return "\n\n".join(initiative.documents)


class FakePromptBuilder:
    def build(self, workflow_name, context):
        return f"Generate PRD for: {context}"


class FakeAIClient:
    def generate(self, prompt):
        return "# Generated PRD\n\nSome content."


class FakeMarkdownWriter:
    def __init__(self):
        self.written = []

    def write(self, content, output_path):
        path = Path(output_path)
        path.write_text(content, encoding="utf-8")
        self.written.append((content, str(output_path)))
        return path


class FakeLogger:
    def info(self, message):
        pass


class FakeValidator:
    def __init__(self):
        self.last_prd = None

    def validate(self, prd_content):
        self.last_prd = prd_content
        return ValidationReport(
            overall_score=7.5,
            summary="Good PRD.",
            sections=[],
        )


def test_create_prd_workflow_with_validation(tmp_path):
    initiative = FakeInitiative(
        name="test-initiative",
        documents=["Document content"],
    )
    repository = FakeRepository([initiative])
    ai_client = FakeAIClient()
    writer = FakeMarkdownWriter()
    validator = FakeValidator()
    output_path = str(tmp_path / "prd.md")

    workflow = CreatePRDWorkflow(
        initiative_repository=repository,
        context_builder=FakeContextBuilder(),
        prompt_builder=FakePromptBuilder(),
        ai_client=ai_client,
        markdown_writer=writer,
        logger=FakeLogger(),
        prd_validator=validator,
    )

    result = workflow.run(output_path)

    assert result.exists()
    assert "# Generated PRD" in result.read_text()

    assert validator.last_prd == "# Generated PRD\n\nSome content."

    assert len(writer.written) == 2
    validation_path = tmp_path / "prd-validation.md"
    assert validation_path.exists()
    assert "7.5" in validation_path.read_text()


def test_create_prd_workflow_without_validation(tmp_path):
    initiative = FakeInitiative(
        name="test-initiative",
        documents=["Document content"],
    )
    repository = FakeRepository([initiative])
    writer = FakeMarkdownWriter()
    output_path = str(tmp_path / "prd.md")

    workflow = CreatePRDWorkflow(
        initiative_repository=repository,
        context_builder=FakeContextBuilder(),
        prompt_builder=FakePromptBuilder(),
        ai_client=FakeAIClient(),
        markdown_writer=writer,
        logger=FakeLogger(),
        prd_validator=None,
    )

    result = workflow.run(output_path)

    assert result.exists()
    assert len(writer.written) == 1


def test_create_prd_without_initiatives_raises_error():
    repository = FakeRepository([])

    workflow = CreatePRDWorkflow(
        initiative_repository=repository,
        context_builder=FakeContextBuilder(),
        prompt_builder=FakePromptBuilder(),
        ai_client=FakeAIClient(),
        markdown_writer=FakeMarkdownWriter(),
        logger=FakeLogger(),
    )

    try:
        workflow.run("/tmp/prd.md")
    except ValueError as error:
        assert "No initiatives found" in str(error)
    else:
        raise AssertionError("Expected ValueError")
