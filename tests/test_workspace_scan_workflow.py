from pathlib import Path

from pm_os.workflows.workspace_scan_workflow import WorkspaceScanWorkflow


class FakeRepository:
    def __init__(self, initiatives):
        self._initiatives = initiatives

    def list_initiatives(self):
        return self._initiatives


class FakeInitiative:
    def __init__(self, name, path):
        self.name = name
        self.path = path


class FakeLogger:
    def info(self, message):
        pass


def test_scan_shows_all_initiatives(tmp_path):
    init1 = tmp_path / "init-1"
    init2 = tmp_path / "init-2"
    init1.mkdir(parents=True, exist_ok=True)
    init2.mkdir(parents=True, exist_ok=True)

    (init1 / "metadata.yaml").write_text(
        "id: INT-0001\nname: Feature A\nstatus: discovery\nowner: alice\n",
        encoding="utf-8",
    )
    (init1 / "artifacts").mkdir(parents=True, exist_ok=True)
    (init1 / "artifacts" / "prd.md").write_text("# PRD", encoding="utf-8")
    (init1 / "artifacts" / "prd-validation.md").write_text(
        "**Overall Score:** 8.0/10", encoding="utf-8"
    )

    (init2 / "metadata.yaml").write_text(
        "id: INT-0002\nname: Feature B\nstatus: development\nowner: bob\n",
        encoding="utf-8",
    )

    repo = FakeRepository([
        FakeInitiative(name="init-1", path=init1),
        FakeInitiative(name="init-2", path=init2),
    ])

    workflow = WorkspaceScanWorkflow(
        initiative_repository=repo,
        logger=FakeLogger(),
    )

    report = workflow.run()

    assert "init-1" in report
    assert "init-2" in report
    assert "alice" in report
    assert "bob" in report
    assert "8.0" in report


def test_scan_with_no_initiatives():
    repo = FakeRepository([])

    workflow = WorkspaceScanWorkflow(
        initiative_repository=repo,
        logger=FakeLogger(),
    )

    report = workflow.run()
    assert "No initiatives found" in report


def test_scan_without_validation_report(tmp_path):
    init = tmp_path / "init-1"
    init.mkdir(parents=True, exist_ok=True)
    (init / "metadata.yaml").write_text(
        "id: INT-0001\nname: Feature A\nstatus: discovery\nowner: alice\n",
        encoding="utf-8",
    )

    repo = FakeRepository([
        FakeInitiative(name="init-1", path=init),
    ])

    workflow = WorkspaceScanWorkflow(
        initiative_repository=repo,
        logger=FakeLogger(),
    )

    report = workflow.run()
    assert "| - |" in report  # score column shows "-"


def test_scan_with_missing_metadata(tmp_path):
    init = tmp_path / "init-1"
    init.mkdir(parents=True, exist_ok=True)

    repo = FakeRepository([
        FakeInitiative(name="init-1", path=init),
    ])

    workflow = WorkspaceScanWorkflow(
        initiative_repository=repo,
        logger=FakeLogger(),
    )

    report = workflow.run()
    assert "init-1" in report
