from pathlib import Path
from typing import Optional

from pm_os.contracts.logger import Logger
from pm_os.contracts.workflow_contracts import (
    AIClientProtocol,
    ContextBuilderProtocol,
    InitiativeRepositoryProtocol,
    MarkdownWriterProtocol,
    PromptBuilderProtocol,
)
from pm_os.infrastructure.guards.scope_guard import ScopeGuard
from pm_os.infrastructure.tracking.change_tracker import ChangeTracker
from pm_os.infrastructure.validators.prd_validator import PRDValidator


class CreatePRDWorkflow:
    """
    Orchestrates the create_prd workflow.

    - Scope Guard: analyzes context before generation
    - Change Tracker: detects what changed since last run
    - PRD Validator: evaluates quality after generation
    """

    def __init__(
        self,
        initiative_repository: InitiativeRepositoryProtocol,
        context_builder: ContextBuilderProtocol,
        prompt_builder: PromptBuilderProtocol,
        ai_client: AIClientProtocol,
        markdown_writer: MarkdownWriterProtocol,
        logger: Logger,
        change_tracker: Optional[ChangeTracker] = None,
        scope_guard: Optional[ScopeGuard] = None,
        prd_validator: Optional[PRDValidator] = None,
    ):
        self.initiative_repository = initiative_repository
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.ai_client = ai_client
        self.markdown_writer = markdown_writer
        self.logger = logger
        self.change_tracker = change_tracker
        self.scope_guard = scope_guard
        self.prd_validator = prd_validator

    def run(self, output_path: str) -> Path:
        self.logger.info("Loading initiatives from workspace.")

        initiatives = self.initiative_repository.list_initiatives()

        if not initiatives:
            raise ValueError("No initiatives found in the workspace.")

        initiative = initiatives[0]
        self.logger.info(f"Selected initiative: {initiative.name}")

        if self.change_tracker:
            self._track_changes(initiative.path)

        self.logger.info("Building context.")
        context = self.context_builder.build(initiative)

        if self.scope_guard:
            self._analyze_scope(context)

        self.logger.info("Building prompt for create_prd workflow.")
        prompt = self.prompt_builder.build(
            workflow_name="create_prd",
            context=context,
        )

        self.logger.info("Generating PRD content with AI client.")
        prd_content = self.ai_client.generate(prompt)

        self.logger.info(f"Writing PRD to {output_path}.")
        output_file = self.markdown_writer.write(
            content=prd_content,
            output_path=output_path,
        )

        if self.prd_validator:
            self._validate_and_report(prd_content, output_path)

        if self.change_tracker:
            self.change_tracker.update_manifest(str(initiative.path))

        self.logger.info("Create PRD workflow completed successfully.")

        return output_file

    def _track_changes(self, initiative_path: Path) -> None:
        changes = self.change_tracker.detect_changes(str(initiative_path))
        if changes:
            self.logger.info(f"Detected {len(changes)} change(s) in context:")
            for c in changes:
                self.logger.info(f"  [{c['change']}] {c['file']}")
        else:
            self.logger.info("No changes detected since last run.")

    def _analyze_scope(self, context: str) -> None:
        self.logger.info("Running scope guard analysis.")
        warnings = self.scope_guard.analyze(context)
        if warnings:
            self.logger.info(f"Scope Guard found {len(warnings)} issue(s):")
            for w in warnings:
                self.logger.info(
                    f"  [{w.get('severity', 'info').upper()}] {w.get('message', '')}"
                )
        else:
            self.logger.info("Scope Guard: no issues detected.")

    def _validate_and_report(self, prd_content: str, prd_path: str) -> None:
        self.logger.info("Validating generated PRD.")
        report = self.prd_validator.validate(prd_content)

        self.logger.info(f"PRD quality score: {report.overall_score}/10")

        validation_path = str(
            Path(prd_path).with_name(
                Path(prd_path).stem + "-validation" + Path(prd_path).suffix
            )
        )

        self.markdown_writer.write(
            content=report.to_markdown(),
            output_path=validation_path,
        )

        self.logger.info(f"Validation report saved to {validation_path}.")
