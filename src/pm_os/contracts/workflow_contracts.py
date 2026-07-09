from pathlib import Path
from typing import Protocol

from pm_os.models import Feature


class FeatureRepositoryProtocol(Protocol):
    def list_features(self) -> list[Feature]:
        ...


class ContextBuilderProtocol(Protocol):
    def build(self, feature: Feature) -> str:
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