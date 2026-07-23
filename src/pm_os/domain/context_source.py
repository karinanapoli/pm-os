from dataclasses import dataclass
from datetime import datetime
from typing import Optional


CONFIDENTIALITY_LEVELS = ("public", "internal", "confidential", "restricted")


@dataclass(frozen=True)
class ContextSource:
    """A traceable unit of context that can be cited by an AI workflow."""

    source_id: str
    name: str
    content: str
    source_type: str
    confidentiality: str = "internal"
    author: str = ""
    modified_at: Optional[datetime] = None
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if self.confidentiality not in CONFIDENTIALITY_LEVELS:
            raise ValueError(f"Invalid confidentiality level: {self.confidentiality}")

    @property
    def estimated_tokens(self) -> int:
        return max(1, (len(self.content) + 3) // 4) if self.content else 0
