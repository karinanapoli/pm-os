from pathlib import Path
from typing import Protocol

from pm_os.domain.initiative import Initiative


class InitiativeRepositoryProtocol(Protocol):
    def list_initiatives(self) -> list[Initiative]:
        ...


class ContextBuilderProtocol(Protocol):
    def build(self, initiative: Initiative) -> str:
        ...


class PromptBuilderProtocol(Protocol):
    def build(self, workflow_name: str, context: str) -> str:
        ...


class AIClientProtocol(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class MarkdownWriterProtocol(Protocol):
    def write(self, content: str, output_path: str) -> Path:
        ...