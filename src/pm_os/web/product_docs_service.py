import hashlib
from pathlib import Path

from pm_os.context_builder import ContextBuilder
from pm_os.domain.context_source import ContextSource
from pm_os.infrastructure.utils import ALLOWED_EXTENSIONS, extract_pdf_text

PRODUCT_DOCS_DIR = Path("workspace/product-docs")


class ProductDocsService:
    def count_docs(self) -> int:
        ctx = PRODUCT_DOCS_DIR / "context"
        if ctx.exists():
            return sum(1 for f in ctx.iterdir() if f.is_file() and f.suffix in ALLOWED_EXTENSIONS)
        return 0

    def load_docs(self) -> list[dict]:
        ctx = PRODUCT_DOCS_DIR / "context"
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
        fp = PRODUCT_DOCS_DIR / "links.json"
        if fp.exists():
            import json
            return json.loads(fp.read_text(encoding="utf-8"))
        return []

    def save_links(self, links: list[dict]):
        import json
        (PRODUCT_DOCS_DIR / "links.json").write_text(
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

    @staticmethod
    def _source_id(value: str) -> str:
        digest = hashlib.sha256(f"product-docs/{value}".encode("utf-8")).hexdigest()
        return f"SRC-{digest[:8].upper()}"
