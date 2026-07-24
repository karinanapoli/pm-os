from pathlib import Path

from pm_os.domain.validation_report import ValidationReport
from pm_os.web.prd_validation_service import PRDValidationService


class FakeValidator:
    def __init__(self, report):
        self.report = report
        self.prd_content = None

    def validate(self, prd_content):
        self.prd_content = prd_content
        return self.report


class FakeWriter:
    def __init__(self):
        self.calls = []

    def write(self, content, output_path):
        self.calls.append((content, output_path))
        path = Path(output_path)
        path.write_text(content, encoding="utf-8")
        return path


def test_validates_versions_and_persists_report(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    prd_path = artifacts_dir / "prd.md"
    prd_path.write_text("# PRD\n\nNew checkout", encoding="utf-8")
    report_path = artifacts_dir / "prd-validation.md"
    report_path.write_text(
        "# PRD Validation Report\n\n**Overall Score:** 6.0/10",
        encoding="utf-8",
    )
    validator = FakeValidator(
        ValidationReport(overall_score=8.0, summary="Much clearer.")
    )
    writer = FakeWriter()

    result = PRDValidationService(
        validator=validator,
        lang="en",
        markdown_writer=writer,
    ).validate(prd_path)

    assert validator.prd_content == "# PRD\n\nNew checkout"
    assert result.report.overall_score == 8.0
    assert result.previous_score == 6.0
    assert result.history[0] == {"score": 8.0, "label": "latest"}
    assert len(result.history) == 2
    assert len(writer.calls) == 1
    assert "8.0/10" in report_path.read_text(encoding="utf-8")
    assert len(list(artifacts_dir.glob("prd-validation-*.md"))) == 1


def test_invalid_response_preserves_last_valid_report(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    prd_path = artifacts_dir / "prd.md"
    prd_path.write_text("# PRD", encoding="utf-8")
    report_path = artifacts_dir / "prd-validation.md"
    previous_content = "# Report\n\n**Overall Score:** 7.0/10"
    report_path.write_text(previous_content, encoding="utf-8")
    writer = FakeWriter()
    validator = FakeValidator(
        ValidationReport(
            overall_score=0,
            summary="Invalid response.",
            is_valid=False,
        )
    )

    result = PRDValidationService(
        validator=validator,
        markdown_writer=writer,
    ).validate(prd_path)

    assert result.report.is_valid is False
    assert result.previous_score == 7.0
    assert result.history == [{"score": 7.0, "label": "latest"}]
    assert report_path.read_text(encoding="utf-8") == previous_content
    assert writer.calls == []
    assert list(artifacts_dir.glob("prd-validation-*.md")) == []
