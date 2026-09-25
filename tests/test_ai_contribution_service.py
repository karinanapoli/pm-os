import pytest

from pm_os.web.ai_contribution_service import AIContributionService


def test_cursor_flow_persists_proposals_and_decisions(tmp_path):
    service = AIContributionService()

    state = service.connect(tmp_path, actor="pm@example.com")
    assert state["connection_status"] == "connected"

    state = service.share(tmp_path, specification_version=2)
    assert state["initiative_access"] == "shared"
    assert state["shared_specification_version"] == 2

    state = service.simulate(tmp_path, specification_version=2)
    assert len(service.pending(state)) == 3

    proposal = service.decide(
        tmp_path,
        "CURSOR-001",
        decision="approved",
        actor="pm@example.com",
    )
    assert proposal["status"] == "approved"
    assert len(service.pending(service.load(tmp_path))) == 2


def test_cannot_share_before_connecting(tmp_path):
    service = AIContributionService()

    with pytest.raises(ValueError, match="connected"):
        service.share(tmp_path, specification_version=1)


def test_proposal_cannot_be_reviewed_twice(tmp_path):
    service = AIContributionService()
    service.connect(tmp_path)
    service.share(tmp_path, specification_version=1)
    service.simulate(tmp_path, specification_version=1)
    service.decide(tmp_path, "CURSOR-001", decision="rejected")

    with pytest.raises(ValueError, match="already"):
        service.decide(tmp_path, "CURSOR-001", decision="approved")


def test_receive_external_proposals_requires_shared_initiative(tmp_path):
    service = AIContributionService()

    with pytest.raises(ValueError, match="not available"):
        service.receive_proposals(
            tmp_path,
            [{
                "field": "requirements",
                "kind": "requirement",
                "content": "Persist progress.",
                "reason": "The current flow loses state.",
            }],
            specification_version=1,
            source="cursor",
        )


def test_receive_external_proposals_and_report_status(tmp_path):
    service = AIContributionService()
    service.connect(tmp_path)
    service.share(tmp_path, specification_version=3)

    received = service.receive_proposals(
        tmp_path,
        [{
            "field": "requirements",
            "kind": "requirement",
            "content": "Persist progress between sessions.",
            "reason": "The code already stores partial answers.",
        }],
        specification_version=3,
        source="cursor",
    )

    assert len(received) == 1
    assert received[0]["id"].startswith("EXT-")
    assert received[0]["status"] == "pending"
    assert service.proposal_status(tmp_path, [received[0]["id"]]) == [{
        "id": received[0]["id"],
        "status": "pending",
        "reviewed_at": "",
    }]


def test_receive_external_proposals_rejects_unknown_field(tmp_path):
    service = AIContributionService()
    service.connect(tmp_path)
    service.share(tmp_path, specification_version=1)

    with pytest.raises(ValueError, match="not allowed"):
        service.receive_proposals(
            tmp_path,
            [{
                "field": "approved_by",
                "kind": "unsafe_change",
                "content": "agent",
                "reason": "bypass review",
            }],
            specification_version=1,
            source="cursor",
        )
