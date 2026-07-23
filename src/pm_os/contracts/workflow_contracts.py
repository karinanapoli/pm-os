from pathlib import Path
from typing import Protocol

from pm_os.domain.initiative import Initiative
from pm_os.domain.validation_report import ValidationReport


class AIProviderError(RuntimeError):
    pass


class InitiativeRepositoryProtocol(Protocol):
    def list_initiatives(self) -> list[Initiative]:
        ...


class ContextBuilderProtocol(Protocol):
    def build(self, initiative: Initiative) -> str:
        ...


class PromptBuilderProtocol(Protocol):
    def build(self, workflow_name: str, context: str, question: str = "", lang: str = "en") -> str:
        ...


class AIClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class MarkdownWriterProtocol(Protocol):
    def write(self, content: str, output_path: str) -> Path:
        ...


class ScopeGuardProtocol(Protocol):
    def analyze(self, context: str) -> list[dict]:
        ...


class ChangeTrackerProtocol(Protocol):
    def detect_changes(self, initiative_path: str) -> list[dict]:
        ...
    def update_manifest(self, initiative_path: str) -> None:
        ...


class PRDValidatorProtocol(Protocol):
    def validate(self, prd_content: str) -> "ValidationReport":
        ...
