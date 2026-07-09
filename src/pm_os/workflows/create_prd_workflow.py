from pathlib import Path

from pm_os.contracts.workflow_contracts import (
    AIClientProtocol,
    ContextBuilderProtocol,
    FeatureRepositoryProtocol,
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
        feature_repository: FeatureRepositoryProtocol,
        context_builder: ContextBuilderProtocol,
        prompt_builder: PromptBuilderProtocol,
        ai_client: AIClientProtocol,
        markdown_writer: MarkdownWriterProtocol,
    ):
        self.feature_repository = feature_repository
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.ai_client = ai_client
        self.markdown_writer = markdown_writer

    def run(self, output_path: str) -> Path:
        features = self.feature_repository.list_features()

        if not features:
            raise ValueError("No features found in the inbox.")

        feature = features[0]

        context = self.context_builder.build(feature)

        prompt = self.prompt_builder.build(
            workflow_name="create_prd",
            context=context,
        )

        prd_content = self.ai_client.generate(prompt)

        return self.markdown_writer.write(
            content=prd_content,
            output_path=output_path,
        )