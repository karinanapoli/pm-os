from dataclasses import dataclass
from pathlib import Path


@dataclass
class Initiative:
    """
    Represents a product initiative inside PM OS.

    An initiative is the main unit of work in the PM OS domain.
    It owns context, artifacts, metadata and workflow history.
    """

    name: str
    path: Path
    documents: list[str]