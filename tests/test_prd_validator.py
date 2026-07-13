from pm_os.domain.validation_report import SectionEvaluation, ValidationReport
from pm_os.infrastructure.validators.prd_validator import PRDValidator


class FakeAIClientForValidator:
    def __init__(self, response: str = ""):
        self.last_prompt = ""
        self.response = response

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


SAMPLE_PRD = """
# PRD - My Feature

## Overview
A new feature.

## Objectives
- Improve user satisfaction
"""


def test_validator_parses_valid_json_response():
    ai_client = FakeAIClientForValidator(response="""
Here is my analysis:

```json
{
  "overall_score": 7.5,
  "summary": "Good PRD with room for improvement.",
  "sections": [
    {
      "name": "Metrics",
      "score": 4.0,
      "issues": ["Metrics are not SMART"],
      "suggestions": ["Define specific targets with timeframes"]
    },
    {
      "name": "Risks",
      "score": 6.0,
      "issues": ["No mitigation plans"],
      "suggestions": ["Add mitigation for each risk"]
    }
  ]
}
```
""")

    validator = PRDValidator(ai_client=ai_client)
    report = validator.validate(SAMPLE_PRD)

    assert isinstance(report, ValidationReport)
    assert report.overall_score == 7.5
    assert "Good PRD" in report.summary
    assert len(report.sections) == 2

    metrics = report.sections[0]
    assert metrics.name == "Metrics"
    assert metrics.score == 4.0
    assert "not SMART" in metrics.issues[0]
    assert "specific targets" in metrics.suggestions[0]

    risks = report.sections[1]
    assert risks.name == "Risks"
    assert risks.score == 6.0


def test_validator_handles_malformed_json():
    ai_client = FakeAIClientForValidator(response="This is not valid JSON at all.")

    validator = PRDValidator(ai_client=ai_client)
    report = validator.validate(SAMPLE_PRD)

    assert report.overall_score == 0.0
    assert "Could not parse" in report.summary


def test_validator_handles_empty_response():
    ai_client = FakeAIClientForValidator(response="")

    validator = PRDValidator(ai_client=ai_client)
    report = validator.validate(SAMPLE_PRD)

    assert report.overall_score == 0.0


def test_validator_builds_prompt_with_prd_content():
    ai_client = FakeAIClientForValidator(response="""```json
{
  "overall_score": 5.0,
  "summary": "Test",
  "sections": []
}
```""")

    validator = PRDValidator(ai_client=ai_client)
    validator.validate(SAMPLE_PRD)

    assert "My Feature" in ai_client.last_prompt
    assert "PRD Content" in ai_client.last_prompt


def test_section_evaluation_defaults():
    section = SectionEvaluation(name="Test", score=8.0)

    assert section.issues == []
    assert section.suggestions == []
