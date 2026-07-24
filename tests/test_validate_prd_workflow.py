from pathlib import Path

import pytest

from pm_os.domain.validation_report import ValidationReport
from pm_os.workflows.validate_prd_workflow import ValidatePRDWorkflow


class FakeValidator:
    def __init__(self, report):
        self.report = report
        self.content = None

    def validate(self, prd_content):
        self.content = prd_content
        return self.report


class FakeWriter:
    def __init__(self):
        self.calls = []

    def write(self, content, output_path):
        self.calls.append((content, output_path))
        path = Path(output_path)
        path.write_text(content, encoding="utf-8")
        return path


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


def build_workflow(validator, writer, logger):
    return ValidatePRDWorkflow(
        initiative_repository=object(),
        ai_client=object(),
        markdown_writer=writer,
        logger=logger,
        prd_validator=validator,
    )


def test_workflow_reads_validates_and_writes_report(tmp_path):
    prd_path = tmp_path / "prd.md"
    prd_path.write_text("# PRD\n\nUseful content", encoding="utf-8")
    output_path = tmp_path / "validation.md"
    validator = FakeValidator(
        ValidationReport(overall_score=8.5, summary="Strong PRD.")
    )
    writer = FakeWriter()
    logger = FakeLogger()

    result = build_workflow(validator, writer, logger).run(
        str(prd_path), str(output_path)
    )

    assert result == output_path
    assert validator.content == "# PRD\n\nUseful content"
    assert len(writer.calls) == 1
    assert "8.5/10" in output_path.read_text(encoding="utf-8")
    assert any("completed successfully" in message for message in logger.messages)


def test_workflow_does_not_write_invalid_ai_response(tmp_path):
    prd_path = tmp_path / "prd.md"
    prd_path.write_text("# PRD", encoding="utf-8")
    writer = FakeWriter()
    validator = FakeValidator(
        ValidationReport(
            overall_score=0,
            summary="Could not parse response.",
            is_valid=False,
        )
    )

    with pytest.raises(ValueError, match="Could not parse"):
        build_workflow(validator, writer, FakeLogger()).run(
            str(prd_path), str(tmp_path / "validation.md")
        )

    assert writer.calls == []
