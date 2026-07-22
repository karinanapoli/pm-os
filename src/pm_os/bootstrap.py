from typing import Optional

from pm_os.contracts.workflow_contracts import AIClient
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


def create_prd_workflow(
    ai_client: Optional[AIClient] = None,
    lang: str = "en",
) -> CreatePRDWorkflow:
    ai_client = ai_client or OllamaClient()
    return CreatePRDWorkflow(
        initiative_repository=InitiativeRepository(),
        context_builder=ContextBuilder(),
        prompt_builder=PromptBuilder(),
        ai_client=ai_client,
        markdown_writer=MarkdownWriter(),
        logger=ConsoleLogger(),
        change_tracker=ChangeTracker(),
        scope_guard=ScopeGuard(ai_client=ai_client),
        prd_validator=PRDValidator(ai_client=ai_client, lang=lang),
    )


def create_validate_prd_workflow(
    ai_client: Optional[AIClient] = None,
    lang: str = "en",
) -> ValidatePRDWorkflow:
    ai_client = ai_client or OllamaClient()
    return ValidatePRDWorkflow(
        initiative_repository=InitiativeRepository(),
        ai_client=ai_client,
        markdown_writer=MarkdownWriter(),
        logger=ConsoleLogger(),
        prd_validator=PRDValidator(ai_client=ai_client, lang=lang),
    )


def create_workspace_scan_workflow() -> WorkspaceScanWorkflow:
    return WorkspaceScanWorkflow(
        initiative_repository=InitiativeRepository(),
        logger=ConsoleLogger(),
    )


def create_scope_guard_instance(ai_client: Optional[AIClient] = None) -> ScopeGuard:
    return ScopeGuard(ai_client=ai_client or OllamaClient())


def create_change_tracker() -> ChangeTracker:
    return ChangeTracker()


def create_prd_validator(ai_client: Optional[AIClient] = None, lang: str = "en") -> PRDValidator:
    return PRDValidator(ai_client=ai_client or OllamaClient(), lang=lang)
