from dataclasses import dataclass, field
from pathlib import Path

from pm_os.domain.context_source import ContextSource


@dataclass
class Initiative:
    """
    Represents a product initiative inside PM OS.

    An initiative is the main unit of work in the PM OS domain.
    It owns context, artifacts, metadata and workflow history.
    """

    name: str
    path: Path
    documents: list[str] = field(default_factory=list)
    sources: list[ContextSource] = field(default_factory=list)

    @property
    def document_count(self) -> int:
        return len(self.sources) if self.sources else len(self.documents)

    @property
    def context_char_count(self) -> int:
        if self.sources:
            return sum(len(source.content) for source in self.sources)
        return sum(len(document) for document in self.documents)

    @property
    def estimated_tokens(self) -> int:
        return max(1, (self.context_char_count + 3) // 4) if self.context_char_count else 0

    @property
    def confidentiality_levels(self) -> list[str]:
        return sorted({source.confidentiality for source in self.sources})
