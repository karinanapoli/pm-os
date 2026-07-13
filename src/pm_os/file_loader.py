from pathlib import Path

from pm_os.models import Feature


class DocumentLoader:
    def load_feature_context(self, feature: Feature) -> str:
        sections = []

        for document in feature.documents:
            content = document.read_text(encoding="utf-8")

            sections.append(
                f"# File: {document.name}\n\n{content}"
            )

        return "\n\n---\n\n".join(sections)
