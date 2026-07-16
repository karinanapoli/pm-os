from pathlib import Path
from typing import Optional

from pm_os.contracts.logger import Logger
from pm_os.contracts.workflow_contracts import (
    AIClient,
    InitiativeRepositoryProtocol,
    MarkdownWriterProtocol,
    PRDValidatorProtocol,
)
from pm_os.infrastructure.validators.prd_validator import PRDValidator


class ValidatePRDWorkflow:
    """
    Orchestrates the validate_prd workflow.

    Reads a PRD from an initiative, validates it using AI,
    and writes a quality report.
    """

    def __init__(
        self,
        initiative_repository: InitiativeRepositoryProtocol,
        ai_client: AIClient,
        markdown_writer: MarkdownWriterProtocol,
        logger: Logger,
        prd_validator: Optional[PRDValidatorProtocol] = None,
    ):
        self.initiative_repository = initiative_repository
        self.ai_client = ai_client
        self.markdown_writer = markdown_writer
        self.logger = logger
        self.prd_validator = prd_validator

    def run(self, prd_path: str, output_path: str) -> Path:
        self.logger.info(f"Reading PRD from {prd_path}.")

        prd_content = Path(prd_path).read_text(encoding="utf-8")

        self.logger.info("Validating PRD content.")
        validator = self.prd_validator or PRDValidator(ai_client=self.ai_client)
        report = validator.validate(prd_content)

        self.logger.info(f"PRD quality score: {report.overall_score}/10")

        self.logger.info(f"Writing validation report to {output_path}.")
        output_file = self.markdown_writer.write(
            content=report.to_markdown(),
            output_path=output_path,
        )

        self.logger.info("Validate PRD workflow completed successfully.")

        return output_file
