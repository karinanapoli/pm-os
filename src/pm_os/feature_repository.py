from pathlib import Path

from pm_os.models import Feature


class FeatureRepository:
    def __init__(self, inbox_path: str = "features/01-inbox"):
        self.inbox_path = Path(inbox_path)

    def list_features(self) -> list[Feature]:
        if not self.inbox_path.exists():
            return []

        features = []

        for path in self.inbox_path.iterdir():
            if path.is_dir():
                documents = [
                    document
                    for document in path.iterdir()
                    if document.is_file()
                ]

                features.append(
                    Feature(
                        name=path.name,
                        path=path,
                        documents=documents,
                    )
                )

        return features