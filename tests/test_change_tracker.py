from pathlib import Path

from pm_os.infrastructure.tracking.change_tracker import ChangeTracker


def test_detect_added_file(tmp_path):
    tracker = ChangeTracker()
    tracker.update_manifest(str(tmp_path))

    new_file = tmp_path / "context" / "novo.md"
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_text("# New content", encoding="utf-8")

    changes = tracker.detect_changes(str(tmp_path))
    assert len(changes) == 1
    assert changes[0]["change"] == "added"
    assert "novo.md" in changes[0]["file"]


def test_detect_modified_file(tmp_path):
    tracker = ChangeTracker()
    ctx = tmp_path / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    (ctx / "doc.md").write_text("original", encoding="utf-8")
    tracker.update_manifest(str(tmp_path))

    (ctx / "doc.md").write_text("modified content", encoding="utf-8")

    changes = tracker.detect_changes(str(tmp_path))
    assert len(changes) == 1
    assert changes[0]["change"] == "modified"


def test_detect_removed_file(tmp_path):
    tracker = ChangeTracker()
    ctx = tmp_path / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    (ctx / "doc.md").write_text("content", encoding="utf-8")
    tracker.update_manifest(str(tmp_path))

    (ctx / "doc.md").unlink()

    changes = tracker.detect_changes(str(tmp_path))
    assert len(changes) == 1
    assert changes[0]["change"] == "removed"


def test_no_changes(tmp_path):
    tracker = ChangeTracker()
    ctx = tmp_path / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    (ctx / "doc.md").write_text("content", encoding="utf-8")
    tracker.update_manifest(str(tmp_path))

    changes = tracker.detect_changes(str(tmp_path))
    assert len(changes) == 0


def test_manifest_is_updated(tmp_path):
    tracker = ChangeTracker()
    ctx = tmp_path / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    (ctx / "doc.md").write_text("content", encoding="utf-8")
    tracker.update_manifest(str(tmp_path))

    manifest_path = tmp_path / ".context_manifest.json"
    assert manifest_path.exists()
    assert "context/doc.md" in manifest_path.read_text()
