from collections.abc import Iterable

from pm_os.domain.context_source import ContextSource
from pm_os.domain.initiative import Initiative


class ContextBuilder:
    """
    Builds the context used by PM OS workflows.
    """

    def build(self, initiative: Initiative) -> str:
        """
        Builds a single context string from all initiative documents.
        """

        if not initiative.sources:
            return "\n\n".join(initiative.documents)

        return self.build_sources(initiative.sources)

    @staticmethod
    def build_sources(sources: Iterable[ContextSource]) -> str:
        """Renders sources with machine-readable boundaries and stable IDs."""
        blocks = []
        for source in sources:
            modified = source.modified_at.isoformat() if source.modified_at else "unknown"
            blocks.append(
                "\n".join([
                    (
                        f'<<<SOURCE id="{source.source_id}" name="{source.name}" '
                        f'type="{source.source_type}" confidentiality="{source.confidentiality}" '
                        f'author="{source.author or "unknown"}" modified="{modified}">>>'
                    ),
                    source.content,
                    f'<<<END SOURCE id="{source.source_id}">>>',
                ])
            )
        return "\n\n".join(blocks)
