from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pm_os.contracts.workflow_contracts import (
    MarkdownWriterProtocol,
    PRDValidatorProtocol,
)
from pm_os.domain.validation_report import ValidationReport
from pm_os.infrastructure.utils import (
    read_validation_history,
    read_validation_score_from_file,
    version_file,
)
from pm_os.writers.markdown_writer import MarkdownWriter


@dataclass(frozen=True)
class PRDValidationResult:
    report: ValidationReport
    prd_content: str
    previous_score: Optional[float]
    history: list[dict]


class PRDValidationService:
    """Validate a PRD and persist only trustworthy reports."""

    def __init__(
        self,
        validator: PRDValidatorProtocol,
        lang: str = "en",
        markdown_writer: Optional[MarkdownWriterProtocol] = None,
    ):
        self.validator = validator
        self.lang = lang
        self.markdown_writer = markdown_writer or MarkdownWriter()

    def validate(self, prd_path: Path) -> PRDValidationResult:
        artifacts_dir = prd_path.parent
        report_path = artifacts_dir / "prd-validation.md"
        previous_score = read_validation_score_from_file(report_path)
        prd_content = prd_path.read_text(encoding="utf-8")
        report = self.validator.validate(prd_content)

        if report.is_valid:
            version_file(report_path)
            self.markdown_writer.write(
                content=report.to_markdown(lang=self.lang),
                output_path=str(report_path),
            )

        return PRDValidationResult(
            report=report,
            prd_content=prd_content,
            previous_score=previous_score,
            history=read_validation_history(artifacts_dir),
        )
