from pm_os.infrastructure.ai.clients.ollama_client import OllamaClient
from pm_os.infrastructure.logging.console_logger import ConsoleLogger
from pm_os.context_builder import ContextBuilder
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.prompt_builder import PromptBuilder
from pm_os.workflows.create_prd_workflow import CreatePRDWorkflow
from pm_os.writers.markdown_writer import MarkdownWriter


def create_prd_workflow() -> CreatePRDWorkflow:
    """
    Creates and wires all dependencies required by the create_prd workflow.

    This is the composition root of the application.
    """

    return CreatePRDWorkflow(
        initiative_repository=InitiativeRepository(),
        context_builder=ContextBuilder(),
        prompt_builder=PromptBuilder(),
        ai_client=OllamaClient(),
        markdown_writer=MarkdownWriter(),
        logger=ConsoleLogger(),
    )
