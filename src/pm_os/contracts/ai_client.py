from typing import Protocol


class AIClient(Protocol):
    """
    Contract for any AI provider used by PM OS.

    Workflows depend on this abstraction, not on concrete providers
    such as FakeAIClient, OllamaClient, OpenAIClient, etc.
    """

    def generate(self, prompt: str) -> str:
        ...