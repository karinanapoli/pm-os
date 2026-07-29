from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from pm_os.domain.signal import Signal


SIGNAL_SOURCE_TYPES = (
    "customer_feedback",
    "research",
    "support",
    "commercial",
    "metric",
    "competitor",
    "internal_hypothesis",
)
SIGNAL_STRENGTHS = ("weak", "medium", "strong")


class SignalRepository:
    """YAML-backed signal memory scoped to the active workspace."""

    def __init__(
        self,
        signals_path: str = "workspace/signals",
        squad_name: Optional[str] = None,
    ):
        self.signals_path = Path(signals_path)
        self.squad_name = squad_name or ""

    def list(self, initiative_id: str = "") -> list[Signal]:
        if not self.signals_path.exists():
            return []
        signals = []
        for path in sorted(self.signals_path.glob("SIG-*.yaml"), reverse=True):
            signal = self._load(path)
            if not signal or signal.squad != self.squad_name:
                continue
            if initiative_id and initiative_id not in signal.initiative_ids:
                continue
            signals.append(signal)
        return signals

    def get(self, signal_id: str) -> Optional[Signal]:
        clean_id = self._clean_id(signal_id)
        if not clean_id:
            return None
        signal = self._load(self.signals_path / f"{clean_id}.yaml")
        if not signal or signal.squad != self.squad_name:
            return None
        return signal

    def create(
        self,
        *,
        title: str,
        summary: str,
        source_type: str,
        theme: str,
        strength: str,
        initiative_ids: Optional[list[str]] = None,
        source_reference: str = "",
        created_by: str = "",
    ) -> Signal:
        title = title.strip()
        summary = summary.strip()
        if not title or not summary:
            raise ValueError("Título e descrição são obrigatórios.")
        if source_type not in SIGNAL_SOURCE_TYPES:
            raise ValueError("Origem do sinal inválida.")
        if strength not in SIGNAL_STRENGTHS:
            raise ValueError("Intensidade do sinal inválida.")
        now = datetime.now(timezone.utc)
        base_id = f"SIG-{now.strftime('%Y%m%d-%H%M%S')}"
        signal_id = base_id
        counter = 1
        while (self.signals_path / f"{signal_id}.yaml").exists():
            signal_id = f"{base_id}-{counter:02d}"
            counter += 1
        signal = Signal(
            signal_id=signal_id,
            title=title,
            summary=summary,
            source_type=source_type,
            theme=theme.strip(),
            strength=strength,
            squad=self.squad_name,
            initiative_ids=sorted(set(initiative_ids or [])),
            source_reference=source_reference.strip(),
            created_at=now.isoformat(),
            created_by=created_by.strip(),
        )
        self._save(signal)
        return signal

    def update_links(self, signal_id: str, initiative_ids: list[str]) -> Optional[Signal]:
        signal = self.get(signal_id)
        if not signal:
            return None
        signal.initiative_ids = sorted(set(initiative_ids))
        self._save(signal)
        return signal

    def _save(self, signal: Signal) -> None:
        self.signals_path.mkdir(parents=True, exist_ok=True)
        path = self.signals_path / f"{signal.signal_id}.yaml"
        payload = {
            "id": signal.signal_id,
            "title": signal.title,
            "summary": signal.summary,
            "source_type": signal.source_type,
            "theme": signal.theme,
            "strength": signal.strength,
            "squad": signal.squad,
            "initiative_ids": signal.initiative_ids,
            "source_reference": signal.source_reference,
            "created_at": signal.created_at,
            "created_by": signal.created_by,
        }
        temporary = path.with_suffix(".yaml.tmp")
        temporary.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _clean_id(signal_id: str) -> str:
        clean = signal_id.strip().upper()
        return clean if re.fullmatch(r"SIG-[A-Z0-9-]+", clean) else ""

    @staticmethod
    def _load(path: Path) -> Optional[Signal]:
        if not path.is_file():
            return None
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return Signal(
                signal_id=str(data.get("id", "")),
                title=str(data.get("title", "")),
                summary=str(data.get("summary", "")),
                source_type=str(data.get("source_type", "")),
                theme=str(data.get("theme", "")),
                strength=str(data.get("strength", "medium")),
                squad=str(data.get("squad", "")),
                initiative_ids=list(data.get("initiative_ids") or []),
                source_reference=str(data.get("source_reference", "")),
                created_at=str(data.get("created_at", "")),
                created_by=str(data.get("created_by", "")),
            )
        except (OSError, yaml.YAMLError, TypeError, ValueError):
            return None
