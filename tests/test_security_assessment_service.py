import json

import pytest

from pm_os.web.security_assessment_service import (
    SecurityAssessmentService,
    SecurityAssessmentValidationError,
)


def test_new_assessment_starts_at_zero(tmp_path):
    result = SecurityAssessmentService().load(tmp_path)

    assert result["score"] == 0.0
    assert len(result["pending"]) == 6


def test_assessment_score_is_transparent_and_persisted(tmp_path):
    service = SecurityAssessmentService()
    submitted = {
        "data_privacy": {"status": "verified", "evidence": "Data map reviewed."},
        "access_control": {"status": "implemented", "evidence": "RBAC enabled."},
        "threat_abuse": {"status": "planned", "action": "Workshop scheduled."},
    }

    saved = service.save(tmp_path, submitted)
    loaded = service.load(tmp_path)

    assert saved["score"] == 3.4
    assert loaded["score"] == saved["score"]
    payload = json.loads((tmp_path / "artifacts" / service.filename).read_text())
    assert payload["answers"]["access_control"]["status"] == "implemented"


def test_invalid_status_is_treated_as_not_assessed(tmp_path):
    result = SecurityAssessmentService().save(
        tmp_path,
        {"data_privacy": {"status": "perfect", "notes": "Unsupported"}},
    )

    assert result["answers"]["data_privacy"]["status"] == "not_assessed"


def test_verified_control_requires_evidence(tmp_path):
    with pytest.raises(SecurityAssessmentValidationError):
        SecurityAssessmentService().save(
            tmp_path,
            {"data_privacy": {"status": "verified", "evidence": ""}},
        )


def test_critical_gap_caps_score(tmp_path):
    submitted = {
        key: {"status": "verified", "evidence": "Reviewed"}
        for key in ("data_privacy", "access_control", "threat_abuse", "data_protection", "compliance", "operations")
    }
    submitted["operations"] = {"status": "planned", "risk": "critical"}

    result = SecurityAssessmentService().save(tmp_path, submitted)

    assert result["score"] == 5.0
    assert result["critical_blockers"] == ["operations"]


def test_identical_submission_does_not_duplicate_history(tmp_path):
    service = SecurityAssessmentService()
    submitted = {
        "data_privacy": {"status": "planned", "action": "Map data flow"},
    }

    first = service.save(tmp_path, submitted, actor="qa@example.com")
    second = service.save(tmp_path, submitted, actor="qa@example.com")

    assert len(first["history"]) == 1
    assert len(second["history"]) == 1
    assert second["updated_at"] == first["updated_at"]


def test_ai_provenance_is_persisted(tmp_path):
    service = SecurityAssessmentService()
    saved = service.save(tmp_path, {"data_privacy": {
        "status": "planned",
        "evidence": "Data map described [SRC-1].",
        "origin": "ai",
        "confidence": "high",
        "source_ids": "SRC-1",
    }})

    assert saved["answers"]["data_privacy"]["origin"] == "ai"
    assert saved["answers"]["data_privacy"]["source_ids"] == "SRC-1"
    assert saved["ai_generated_count"] == 1
