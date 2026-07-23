import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Optional

from pm_os.context_builder import ContextBuilder
from pm_os.domain.context_source import ContextSource
from pm_os.infrastructure.utils import ALLOWED_EXTENSIONS, extract_pdf_text

PRODUCT_DOCS_DIR = Path("workspace/product-docs")


class ProductDocsService:
    def __init__(
        self,
        owner_email: str = "",
        squad_name: str = "",
        root_dir: Optional[Path] = None,
    ):
        root = root_dir or PRODUCT_DOCS_DIR
        if squad_name:
            safe_squad = re.sub(r"[^a-zA-Z0-9_-]", "-", squad_name).strip("-") or "default"
            self.base_dir = root / "squads" / safe_squad
            self.scope_key = f"squad/{safe_squad}"
        elif owner_email:
            owner_hash = hashlib.sha256(owner_email.strip().lower().encode("utf-8")).hexdigest()[:16]
            self.base_dir = root / "personal" / owner_hash
            self.scope_key = f"personal/{owner_hash}"
        else:
            # Backward-compatible service for CLI and direct library consumers.
            self.base_dir = root
            self.scope_key = "legacy"

    @property
    def context_dir(self) -> Path:
        return self.base_dir / "context"

    def migrate_legacy_if_empty(self, legacy_root: Optional[Path] = None) -> bool:
        """Copy a legacy single-user library into an empty scoped library."""
        if self.scope_key == "legacy" or self.base_dir.exists():
            return False
        legacy = legacy_root or PRODUCT_DOCS_DIR
        legacy_context = legacy / "context"
        legacy_links = legacy / "links.json"
        docs = (
            [path for path in legacy_context.iterdir() if path.is_file()]
            if legacy_context.exists() else []
        )
        if not docs and not legacy_links.is_file():
            return False
        self.context_dir.mkdir(parents=True, exist_ok=True)
        for document in docs:
            if document.suffix in ALLOWED_EXTENSIONS:
                shutil.copy2(document, self.context_dir / document.name)
        if legacy_links.is_file():
            shutil.copy2(legacy_links, self.base_dir / "links.json")
        return True

    def count_docs(self) -> int:
        ctx = self.context_dir
        if ctx.exists():
            return sum(1 for f in ctx.iterdir() if f.is_file() and f.suffix in ALLOWED_EXTENSIONS)
        return 0

    def load_docs(self) -> list[dict]:
        ctx = self.context_dir
        docs = []
        if ctx.exists():
            for f in sorted(ctx.iterdir()):
                if f.is_file() and f.suffix in ALLOWED_EXTENSIONS:
                    if f.suffix == ".pdf":
                        content = extract_pdf_text(f)
                    else:
                        content = f.read_text(encoding="utf-8")
                    docs.append({"name": f.name, "content": content})
        return docs

    def load_links(self) -> list[dict]:
        fp = self.base_dir / "links.json"
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
        return []

    def save_links(self, links: list[dict]):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "links.json").write_text(
            json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def build_context(self) -> str:
        sources = []
        for d in self.load_docs():
            sources.append(ContextSource(
                source_id=self._source_id(f"document/{d['name']}"),
                name=d["name"],
                content=d["content"],
                source_type=Path(d["name"]).suffix.lstrip(".") or "text",
                confidentiality="internal",
                size_bytes=len(d["content"].encode("utf-8")),
            ))
        for link in self.load_links():
            sources.append(ContextSource(
                source_id=self._source_id(f"link/{link['url']}"),
                name=link["title"],
                content=link["url"],
                source_type="link",
                confidentiality="internal",
                size_bytes=len(link["url"].encode("utf-8")),
            ))
        return ContextBuilder.build_sources(sources)

    def _source_id(self, value: str) -> str:
        digest = hashlib.sha256(
            f"product-docs/{self.scope_key}/{value}".encode("utf-8")
        ).hexdigest()
        return f"SRC-{digest[:8].upper()}"
