from pm_os.infrastructure.ai.clients.ollama_client import OllamaClient
from pm_os.infrastructure.logging.console_logger import ConsoleLogger
from pm_os.infrastructure.guards.scope_guard import ScopeGuard
from pm_os.infrastructure.tracking.change_tracker import ChangeTracker
from pm_os.infrastructure.validators.prd_validator import PRDValidator
from pm_os.context_builder import ContextBuilder
from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.prompt_builder import PromptBuilder
from pm_os.workflows.create_prd_workflow import CreatePRDWorkflow
from pm_os.workflows.validate_prd_workflow import ValidatePRDWorkflow
from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow
from pm_os.writers.markdown_writer import MarkdownWriter


def create_prd_workflow() -> CreatePRDWorkflow:
    """
    Creates and wires all dependencies for the create_prd workflow.
    Includes Change Tracker, Scope Guard, and PRD Validator.
    """

    ai_client = OllamaClient()

    return CreatePRDWorkflow(
        initiative_repository=InitiativeRepository(),
        context_builder=ContextBuilder(),
        prompt_builder=PromptBuilder(),
        ai_client=ai_client,
        markdown_writer=MarkdownWriter(),
        logger=ConsoleLogger(),
        change_tracker=ChangeTracker(),
        scope_guard=ScopeGuard(ai_client=ai_client),
        prd_validator=PRDValidator(ai_client=ai_client, lang="en"),
    )


def create_validate_prd_workflow() -> ValidatePRDWorkflow:
    """
    Creates and wires all dependencies for the validate_prd workflow.
    """

    return ValidatePRDWorkflow(
        initiative_repository=InitiativeRepository(),
        ai_client=OllamaClient(),
        markdown_writer=MarkdownWriter(),
        logger=ConsoleLogger(),
    )


def create_workspace_scan_workflow() -> WorkspaceScanWorkflow:
    """
    Creates and wires all dependencies for the workspace scan workflow.
    """

    return WorkspaceScanWorkflow(
        initiative_repository=InitiativeRepository(),
        logger=ConsoleLogger(),
    )


def create_scope_guard_instance() -> ScopeGuard:
    """
    Creates a standalone ScopeGuard instance for CLI use.
    """

    return ScopeGuard(ai_client=OllamaClient())
