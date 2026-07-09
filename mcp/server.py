from pm_os.feature_repository import FeatureRepository
from pm_os.file_loader import DocumentLoader


repo = FeatureRepository()
loader = DocumentLoader()

features = repo.list_features()

print("Features encontradas:")

for index, feature in enumerate(features, start=1):
    print(f"{index}. {feature.name}")

    context = loader.load_feature_context(feature)

    print("\nContexto consolidado:")
    print(context)