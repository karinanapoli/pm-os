import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

ALLOWED_EXTENSIONS = frozenset({
    ".md", ".txt", ".csv", ".json", ".yaml", ".yml",
    ".rst", ".toml", ".pdf",
})


def parse_validation_score(content: str) -> Optional[float]:
    for line in content.splitlines():
        if "Overall Score:" in line or "Nota Geral:" in line:
            try:
                score_str = line.split("**")[-1].split("/")[0].strip()
                return float(score_str)
            except (ValueError, IndexError):
                pass
    m = re.search(r"\*\*Overall Score[:\*]+\s*([\d.]+)", content)
    if m:
        return float(m.group(1))
    m = re.search(r"\*\*Nota Geral[:\*]+\s*([\d.]+)", content)
    if m:
        return float(m.group(1))
    return None


def read_validation_score_from_file(report_path: Path) -> Optional[float]:
    if not report_path.exists():
        return None
    try:
        content = report_path.read_text(encoding="utf-8")
        return parse_validation_score(content)
    except (OSError, ValueError):
        return None


def read_validation_history(artifacts_dir: Path) -> list[dict]:
    if not artifacts_dir.exists():
        return []

    current_score = read_validation_score_from_file(artifacts_dir / "prd-validation.md")
    entries = []
    if current_score is not None:
        entries.append({
            "score": current_score,
            "label": "latest",
        })

    pattern = re.compile(r"prd-validation-(\d{8}_\d{6})\.md$")
    for f in sorted(artifacts_dir.iterdir(), reverse=True):
        m = pattern.match(f.name)
        if m:
            score = read_validation_score_from_file(f)
            if score is not None:
                timestamp = m.group(1)
                date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
                entries.append({"score": score, "label": date_str})

    seen = set()
    deduped = []
    for e in entries:
        key = (e["score"], e["label"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    return deduped


def version_file(filepath: Path) -> Optional[Path]:
    if not filepath.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_path = filepath.with_name(f"{filepath.stem}-{ts}{filepath.suffix}")
    try:
        content = filepath.read_text(encoding="utf-8")
        version_path.write_text(content, encoding="utf-8")
        return version_path
    except OSError:
        return None


def parse_json_from_ai_response(response: str) -> Optional[dict]:
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
    if not json_match:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        return None
    raw = json_match.group(1) if "```" in response else json_match.group(0)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(path)
        texts = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        return "\n".join(texts)
    except Exception:
        return ""
