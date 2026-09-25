from pathlib import Path

import pytest

from pm_os.web.ai_contribution_service import AIContributionService
from pm_os.web.cursor_mcp_service import CursorMCPService
from pm_os.web.product_specification_service import ProductSpecificationService, SPECIFICATION_FIELDS


def _initiative(workspace: Path, name: str = "INT-001") -> Path:
    path = workspace / "initiatives" / name
    (path / "context").mkdir(parents=True)
    (path / "context" / "brief.md").write_text("Users abandon onboarding.", encoding="utf-8")
    (path / "metadata.yaml").write_text("name: Onboarding\n", encoding="utf-8")
    sections = {field: "" for field in SPECIFICATION_FIELDS}
    sections.update({
        "problem": "Users abandon onboarding.",
        "requirements": "Show progress.",
    })
    ProductSpecificationService().save(path, sections, actor="pm@example.com")
    return path


def _share(path: Path) -> None:
    service = AIContributionService()
    service.connect(path, actor="pm@example.com")
    service.share(path, specification_version=1)


def test_lists_only_explicitly_shared_initiatives(tmp_path):
    shared = _initiative(tmp_path, "INT-SHARED")
    _initiative(tmp_path, "INT-PRIVATE")
    _share(shared)

    initiatives = CursorMCPService(tmp_path).list_initiatives()

    assert [item["id"] for item in initiatives] == ["INT-SHARED"]
    assert initiatives[0]["title"] == "Onboarding"


def test_rejects_context_access_for_private_initiative(tmp_path):
    _initiative(tmp_path)

    with pytest.raises(ValueError, match="not shared"):
        CursorMCPService(tmp_path).get_initiative_context("INT-001")


def test_returns_context_and_structured_specification(tmp_path):
    path = _initiative(tmp_path)
    _share(path)

    result = CursorMCPService(tmp_path).get_initiative_context("INT-001")

    assert "Users abandon onboarding." in result["context"]
    assert result["specification"]["version"] == 1
    assert result["specification"]["sections"]["requirements"] == "Show progress."


def test_cursor_can_submit_proposals_for_human_review(tmp_path):
    path = _initiative(tmp_path)
    _share(path)
    service = CursorMCPService(tmp_path)

    receipt = service.propose_changes(
        "INT-001",
        specification_version=1,
        proposals=[{
            "field": "acceptance_criteria",
            "kind": "acceptance_criterion",
            "content": "Progress updates after each step.",
            "reason": "Makes the progress requirement testable.",
        }],
    )

    assert receipt["status"] == "pending_review"
    assert receipt["stale"] is False
    statuses = service.get_proposal_status("INT-001", receipt["proposal_ids"])
    assert statuses[0]["status"] == "pending"


def test_cursor_can_submit_referenced_technical_discovery(tmp_path):
    path = _initiative(tmp_path)
    _share(path)

    proposal = CursorMCPService(tmp_path).add_technical_discovery(
        "INT-001",
        summary="Partial progress is already persisted.",
        reason="This changes the implementation scope.",
        specification_version=1,
        references=["src/onboarding/store.py:42"],
    )

    assert proposal["kind"] == "technical_discovery"
    assert "store.py:42" in proposal["content"]
    assert proposal["status"] == "pending"


def test_prd_is_available_only_after_sharing(tmp_path):
    path = _initiative(tmp_path)
    (path / "artifacts" / "prd.md").write_text("# PRD", encoding="utf-8")
    service = CursorMCPService(tmp_path)

    with pytest.raises(ValueError, match="not shared"):
        service.get_prd("INT-001")

    _share(path)
    assert service.get_prd("INT-001") == "# PRD"
