import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class InitiativeChatService:
    """Persist a small, auditable conversation alongside an initiative."""

    def __init__(self, max_messages: int = 40):
        self.max_messages = max(2, max_messages)

    def load(self, initiative_path: Path) -> list[dict]:
        path = self._path(initiative_path)
        if not path.is_file():
            return []
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(value, list):
            return []
        return [item for item in value if self._valid(item)][-self.max_messages:]

    def append_exchange(
        self,
        initiative_path: Path,
        *,
        question: str,
        answer: str,
        actor: str = "",
        sources: Optional[list[str]] = None,
        mcp_used: Optional[list[str]] = None,
    ) -> list[dict]:
        history = self.load(initiative_path)
        now = datetime.now(timezone.utc).isoformat()
        history.extend([
            {"role": "user", "content": question.strip(), "actor": actor, "created_at": now},
            {
                "role": "assistant",
                "content": answer.strip(),
                "sources": sources or [],
                "mcp_used": mcp_used or [],
                "created_at": now,
            },
        ])
        history = history[-self.max_messages:]
        path = self._path(initiative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        return history

    def clear(self, initiative_path: Path) -> None:
        path = self._path(initiative_path)
        if path.exists():
            path.unlink()

    @staticmethod
    def _path(initiative_path: Path) -> Path:
        return initiative_path / "artifacts" / "assistant-chat.json"

    @staticmethod
    def _valid(item: object) -> bool:
        return (
            isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and isinstance(item.get("content"), str)
            and bool(item["content"].strip())
        )
