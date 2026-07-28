from pm_os.repositories.initiative_repository import InitiativeRepository
from pm_os.web.initiative_lifecycle_service import (
    InitiativeLifecycleService,
    InvalidInitiativeId,
)
import pytest
import yaml


class FakeTracker:
    def update_manifest(self, path):
        pass


def service(tmp_path):
    repository = InitiativeRepository(initiatives_path=tmp_path / "initiatives")
    return InitiativeLifecycleService(repository, FakeTracker), repository


def test_create_generates_unique_id_and_metadata(tmp_path):
    lifecycle, repository = service(tmp_path)

    first = lifecycle.create("Checkout Growth", context="Research")
    second = lifecycle.create("Checkout Growth")

    assert first == "INT-CHECKOUT-GROWTH"
    assert second == "INT-CHECKOUT-GROWTH-001"
    assert (repository.initiatives_path / first / "context" / "context.md").read_text() == "Research"
    assert (repository.initiatives_path / first / "metadata.yaml").exists()


def test_create_preserves_quick_mode_and_accepts_guided_mode(tmp_path):
    lifecycle, repository = service(tmp_path)
    quick = lifecycle.create("Quick")
    guided = lifecycle.create("Guided", experience_mode="guided")

    quick_meta = yaml.safe_load(
        (repository.initiatives_path / quick / "metadata.yaml").read_text()
    )
    guided_meta = yaml.safe_load(
        (repository.initiatives_path / guided / "metadata.yaml").read_text()
    )
    assert quick_meta["experience_mode"] == "quick"
    assert guided_meta["experience_mode"] == "guided"


def test_create_rejects_unsafe_explicit_id(tmp_path):
    lifecycle, _ = service(tmp_path)

    with pytest.raises(InvalidInitiativeId):
        lifecycle.create("Unsafe", initiative_id="../outside")


def test_archive_list_and_restore_preserve_original_name(tmp_path):
    lifecycle, repository = service(tmp_path)
    lifecycle.create("Original", initiative_id="INT-ORIGINAL")

    archived_name = lifecycle.archive("INT-ORIGINAL")
    archived = lifecycle.list_archived()
    restored_name = lifecycle.restore(archived_name)

    assert archived[0]["name"] == archived_name
    assert archived[0]["archived_at"]
    assert restored_name == "INT-ORIGINAL"
    assert (repository.initiatives_path / "INT-ORIGINAL").is_dir()


def test_restore_rejects_traversal_and_resolves_collisions(tmp_path):
    lifecycle, _ = service(tmp_path)
    lifecycle.create("Original", initiative_id="INT-ORIGINAL")
    archived_name = lifecycle.archive("INT-ORIGINAL")
    lifecycle.create("Replacement", initiative_id="INT-ORIGINAL")

    assert lifecycle.restore("../../sensitive") is None
    assert lifecycle.restore(archived_name) == "INT-ORIGINAL-restored-001"
