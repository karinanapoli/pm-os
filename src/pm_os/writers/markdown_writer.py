from pathlib import Path


class MarkdownWriter:
    """
    Persists Markdown content to the workspace.

    The writer is intentionally dumb:
    it does not know anything about AI,
    PRDs or prompts.

    It only writes Markdown to disk.
    """

    def write(self, content: str, output_path: str) -> Path:
        path = Path(output_path)

        # Creates folders if necessary
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")

        return path