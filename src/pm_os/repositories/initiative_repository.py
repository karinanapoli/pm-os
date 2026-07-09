from pathlib import Path

from pm_os.domain.initiative import Initiative


class InitiativeRepository:
    """
    Loads product initiatives from the PM OS workspace.
    """

    def __init__(
        self,
        initiatives_path: str = "workspace/initiatives",
    ):
        self.initiatives_path = Path(initiatives_path)

    def list_initiatives(self) -> list[Initiative]:
        """
        Lists all initiatives available in the workspace.
        """

        if not self.initiatives_path.exists():
            return []

        initiatives: list[Initiative] = []

        for initiative_path in self.initiatives_path.iterdir():
            if not initiative_path.is_dir():
                continue

            context_path = initiative_path / "context"

            documents: list[str] = []

            if context_path.exists():
                for document_path in context_path.glob("*.md"):
                    documents.append(document_path.read_text())

            initiatives.append(
                Initiative(
                    name=initiative_path.name,
                    path=initiative_path,
                    documents=documents,
                )
            )

        return initiatives