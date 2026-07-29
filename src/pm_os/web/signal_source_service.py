from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from pm_os.infrastructure.utils import extract_pdf_text, safe_upload_filename


SIGNAL_SOURCE_EXTENSIONS = frozenset({".pdf", ".md", ".txt"})


class SignalSourceError(ValueError):
    pass


class SignalSourceService:
    def __init__(
        self,
        root: str = "workspace/signals/sources",
        squad_name: str = "",
    ):
        self.root = Path(root)
        self.squad_name = squad_name or ""

    def save(self, filename: str, content: bytes, created_by: str = "") -> dict:
        clean_name = safe_upload_filename(filename)
        suffix = Path(clean_name).suffix.lower()
        if not clean_name:
            raise SignalSourceError("upload.invalid_filename")
        if suffix not in SIGNAL_SOURCE_EXTENSIONS:
            raise SignalSourceError("signals.upload.invalid_type")
        scoped_content = self.squad_name.encode("utf-8") + b"\0" + content
        digest = hashlib.sha256(scoped_content).hexdigest()[:10].upper()
        source_id = f"SSRC-{digest}"
        directory = self.root / source_id
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / clean_name
        file_path.write_bytes(content)
        metadata = {
            "id": source_id,
            "filename": clean_name,
            "squad": self.squad_name,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(content),
        }
        (directory / "metadata.yaml").write_text(
            yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return metadata

    def get(self, source_id: str) -> Optional[dict]:
        if not re.fullmatch(r"SSRC-[A-F0-9]{10}", source_id or ""):
            return None
        directory = self.root / source_id
        metadata_path = directory / "metadata.yaml"
        if not metadata_path.is_file():
            return None
        try:
            metadata = yaml.safe_load(
                metadata_path.read_text(encoding="utf-8")
            ) or {}
        except (OSError, yaml.YAMLError):
            return None
        if str(metadata.get("squad", "")) != self.squad_name:
            return None
        filename = safe_upload_filename(str(metadata.get("filename", "")))
        file_path = directory / filename
        if not filename or not file_path.is_file():
            return None
        metadata["path"] = file_path
        return metadata

    def extract_text(self, source: dict) -> str:
        path = source["path"]
        try:
            if path.suffix.lower() == ".pdf":
                text = extract_pdf_text(path)
            else:
                text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, RuntimeError) as exc:
            raise SignalSourceError("signals.upload.read_error") from exc
        if not text.strip():
            raise SignalSourceError("signals.upload.empty")
        return text.strip()

    def suggest(
        self,
        text: str,
        filename: str,
        ai_client=None,
        lang: str = "pt-BR",
    ) -> list[dict]:
        return self.suggest_with_metadata(text, filename, ai_client, lang)[0]

    def suggest_with_metadata(
        self,
        text: str,
        filename: str,
        ai_client=None,
        lang: str = "pt-BR",
    ) -> tuple[list[dict], bool]:
        if ai_client is not None:
            try:
                generated = ai_client.generate(self._prompt(text, filename, lang))
                suggestions = self._parse_ai_suggestions(generated)
                if suggestions:
                    return suggestions, True
            except Exception:
                pass
        return self._local_suggestions(text), False

    @staticmethod
    def _local_suggestions(text: str) -> list[dict]:
        cleaned = re.sub(r"(?m)^#{1,6}\s+", "", text)
        paragraphs = [
            re.sub(r"\s+", " ", paragraph).strip(" -*")
            for paragraph in re.split(r"\n\s*\n", cleaned)
        ]
        candidates = [item for item in paragraphs if len(item) >= 40][:3]
        if not candidates:
            candidates = [re.sub(r"\s+", " ", cleaned).strip()[:800]]
        suggestions = []
        for paragraph in candidates:
            first_sentence = re.split(r"(?<=[.!?])\s+", paragraph, maxsplit=1)[0]
            title = first_sentence[:100].rstrip(" .,:;")
            suggestions.append({
                "title": title or "Evidência encontrada no documento",
                "summary": paragraph[:1200],
                "theme": "",
                "strength": "medium",
                "source_type": "research",
            })
        return suggestions

    @staticmethod
    def _prompt(text: str, filename: str, lang: str) -> str:
        response_language = "English" if lang == "en" else "Português do Brasil"
        return f"""Você é um pesquisador de produto. Analise a fonte abaixo e extraia
até 5 sinais distintos que possam apoiar decisões de produto. Não invente fatos.
Responda SOMENTE com um array JSON. Cada item deve conter: title, summary,
theme, strength (weak, medium ou strong) e source_type (customer_feedback,
research, support, commercial, metric, competitor ou internal_hypothesis).
O summary deve preservar a evidência observada, sem transformá-la em solução.
Escreva title, summary e theme em: {response_language}.

Fonte: {filename}
Conteúdo:
{text[:12000]}
"""

    @staticmethod
    def _parse_ai_suggestions(value: str) -> list[dict]:
        match = re.search(r"\[[\s\S]*\]", value or "")
        if not match:
            return []
        try:
            items = json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return []
        suggestions = []
        for item in items[:5] if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
            strength = str(item.get("strength", "medium"))
            source_type = str(item.get("source_type", "research"))
            if not title or not summary:
                continue
            suggestions.append({
                "title": title[:140],
                "summary": summary[:1600],
                "theme": str(item.get("theme", ""))[:80],
                "strength": strength if strength in {"weak", "medium", "strong"} else "medium",
                "source_type": source_type,
            })
        return suggestions
