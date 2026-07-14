from pathlib import Path

PRODUCT_DOCS_DIR = Path("workspace/product-docs")


class ProductDocsService:
    def count_docs(self) -> int:
        ctx = PRODUCT_DOCS_DIR / "context"
        if ctx.exists():
            return sum(1 for f in ctx.iterdir() if f.is_file() and f.suffix in (".md", ".txt"))
        return 0

    def load_docs(self) -> list[dict]:
        ctx = PRODUCT_DOCS_DIR / "context"
        docs = []
        if ctx.exists():
            for f in sorted(ctx.iterdir()):
                if f.is_file() and f.suffix in (".md", ".txt"):
                    docs.append({"name": f.name, "content": f.read_text(encoding="utf-8")})
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
        parts = []
        for d in self.load_docs():
            parts.append(f"--- Documentação complementar: {d['name']} ---\n\n{d['content']}")
        links = self.load_links()
        if links:
            lines = "\n".join(f"- {l['title']}: {l['url']}" for l in links)
            parts.append(f"--- Links de Referência do Produto ---\n\n{lines}")
        return "\n\n".join(parts)
