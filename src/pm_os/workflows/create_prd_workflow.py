from pathlib import Path

from pm_os.contracts.logger import Logger
from pm_os.contracts.workflow_contracts import (
    AIClientProtocol,
    ContextBuilderProtocol,
    InitiativeRepositoryProtocol,
    MarkdownWriterProtocol,
    PromptBuilderProtocol,
)


class CreatePRDWorkflow:
    """
    Orchestrates the create_prd workflow.

    This workflow depends on contracts, not concrete implementations.
    """

    def __init__(
        self,
        initiative_repository: InitiativeRepositoryProtocol,
        context_builder: ContextBuilderProtocol,
        prompt_builder: PromptBuilderProtocol,
        ai_client: AIClientProtocol,
        markdown_writer: MarkdownWriterProtocol,
        logger: Logger,
    ):
        self.initiative_repository = initiative_repository
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.ai_client = ai_client
        self.markdown_writer = markdown_writer
        self.logger = logger

    def run(self, output_path: str) -> Path:
        self.logger.info("Loading initiatives from workspace.")

        initiatives = self.initiative_repository.list_initiatives()

        if not initiatives:
            raise ValueError("No initiatives found in the workspace.")

        initiative = initiatives[0]
        self.logger.info(f"Selected initiative: {initiative.name}")

        self.logger.info("Building context.")
        context = self.context_builder.build(initiative)

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

        self.logger.info("Create PRD workflow completed successfully.")

        return output_file