from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient
from pm_os.context_builder import ContextBuilder
from pm_os.feature_repository import FeatureRepository
from pm_os.prompt_builder import PromptBuilder
from pm_os.workflows.create_prd_workflow import CreatePRDWorkflow
from pm_os.writers.markdown_writer import MarkdownWriter


def create_prd_workflow() -> CreatePRDWorkflow:
    """
    Creates and wires all dependencies required by the create_prd workflow.

    This is the composition root of the application.
    """
    return CreatePRDWorkflow(
        feature_repository=FeatureRepository(),
        context_builder=ContextBuilder(),
        prompt_builder=PromptBuilder(),
       ai_client=FakeAIClient(),
        markdown_writer=MarkdownWriter(),
    )