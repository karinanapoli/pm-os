from dataclasses import dataclass
from pathlib import Path


@dataclass
class Feature:
    name: str
    path: Path
    documents: list[Path]