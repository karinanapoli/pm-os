import json

import pytest

from pm_os.web.security_assessment_ai_service import (
    SecurityAssessmentAIService,
    SecurityAssessmentGenerationError,
)
from pm_os.web.security_assessment_service import SecurityAssessmentService


class StubAIClient:
    def __init__(self, response):
        self.response = response
        self.prompt = ""

    def generate(self, prompt):
        self.prompt = prompt
        return self.response


def _context():
    return '''<<<SOURCE id="SRC-CONTEXT" name="context.md" type="context" confidentiality="internal" author="PM" modified="unknown">>>
The product stores supplier tax data and uses role-based access control.
<<<END SOURCE id="SRC-CONTEXT">>>'''


def test_generates_source_grounded_assessment_and_explicit_gaps(tmp_path):
    response = json.dumps({"answers": {
        "data_privacy": {
            "status": "implemented", "risk": "high",
            "evidence": "Supplier tax data is stored [SRC-CONTEXT].",
            "action": "Define retention.", "confidence": "high",
            "source_ids": ["SRC-CONTEXT"],
        },
        "operations": {
            "status": "not_assessed", "risk": "medium", "evidence": "",
            "action": "How are incidents handled?", "confidence": "low", "source_ids": [],
        },
    }})
    client = StubAIClient(response)
    existing = SecurityAssessmentService().load(tmp_path)

    result = SecurityAssessmentAIService().generate(client, _context(), existing, "pt-BR")

    assert result["answers"]["data_privacy"]["status"] == "implemented"
    assert result["answers"]["data_privacy"]["origin"] == "ai"
    assert result["answers"]["data_privacy"]["source_ids"] == "SRC-CONTEXT"
    assert result["answers"]["operations"]["status"] == "not_assessed"
    assert "Brazilian Portuguese" in client.prompt


def test_downgrades_claim_without_a_valid_source(tmp_path):
    response = json.dumps({"answers": {"access_control": {
        "status": "implemented", "risk": "low", "evidence": "RBAC exists [MADE-UP].",
        "action": "", "confidence": "high", "source_ids": ["MADE-UP"],
    }}})

    result = SecurityAssessmentAIService().generate(
        StubAIClient(response), _context(), SecurityAssessmentService().load(tmp_path)
    )

    assert result["answers"]["access_control"]["status"] == "not_assessed"
    assert result["answers"]["access_control"]["evidence"] == ""


def test_never_overwrites_human_verified_answer(tmp_path):
    service = SecurityAssessmentService()
    existing = service.save(tmp_path, {
        "data_privacy": {"status": "verified", "evidence": "Reviewed by Security."},
    })
    response = json.dumps({"answers": {"data_privacy": {
        "status": "not_assessed", "risk": "critical", "evidence": "",
        "action": "Start over", "confidence": "low", "source_ids": [],
    }}})

    result = SecurityAssessmentAIService().generate(StubAIClient(response), _context(), existing)

    assert result["answers"]["data_privacy"]["status"] == "verified"
    assert result["answers"]["data_privacy"]["evidence"] == "Reviewed by Security."


def test_never_overwrites_existing_manual_answer(tmp_path):
    service = SecurityAssessmentService()
    existing = service.save(tmp_path, {"access_control": {
        "status": "planned", "evidence": "Decision workshop notes.", "origin": "manual",
    }})
    response = json.dumps({"answers": {"access_control": {
        "status": "implemented", "risk": "low", "evidence": "RBAC [SRC-CONTEXT].",
        "action": "", "confidence": "high", "source_ids": ["SRC-CONTEXT"],
    }}})

    result = SecurityAssessmentAIService().generate(StubAIClient(response), _context(), existing)

    assert result["answers"]["access_control"]["status"] == "planned"
    assert result["answers"]["access_control"]["origin"] == "manual"


def test_rejects_invalid_provider_response(tmp_path):
    with pytest.raises(SecurityAssessmentGenerationError):
        SecurityAssessmentAIService().generate(
            StubAIClient("not json"), _context(), SecurityAssessmentService().load(tmp_path)
        )
