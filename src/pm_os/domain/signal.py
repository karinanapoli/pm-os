from dataclasses import dataclass, field


@dataclass
class Signal:
    signal_id: str
    title: str
    summary: str
    source_type: str
    theme: str
    strength: str
    squad: str = ""
    initiative_ids: list[str] = field(default_factory=list)
    source_reference: str = ""
    created_at: str = ""
    created_by: str = ""

