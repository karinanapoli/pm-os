from pm_os.domain.validation_report import SectionEvaluation, ValidationReport
from pm_os.infrastructure.validators.prd_validator import PRDValidator


class FakeAIClientForValidator:
    def __init__(self, response: str = ""):
        self.last_prompt = ""
        self.response = response

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


class IncompleteLocalAIClient(FakeAIClientForValidator):
    def generate_with_limit(self, prompt: str, max_tokens: int) -> str:
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
    assert report.is_valid is False


def test_validator_handles_empty_response():
    ai_client = FakeAIClientForValidator(response="")

    validator = PRDValidator(ai_client=ai_client)
    report = validator.validate(SAMPLE_PRD)

    assert report.overall_score == 0.0
    assert report.is_valid is False


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


def test_validator_normalizes_untrusted_ai_fields():
    ai_client = FakeAIClientForValidator(response="""```json
{
  "overall_score": 12,
  "summary": 42,
  "sections": [
    {
      "name": "  Metrics  ",
      "score": -3,
      "issues": ["Missing target", 99, ""],
      "suggestions": "not-a-list",
      "rationale": false,
      "action_items": ["Define a target"]
    },
    "not-an-object"
  ]
}
```""")

    report = PRDValidator(ai_client=ai_client).validate(SAMPLE_PRD)

    assert report.is_valid is True
    assert report.overall_score == 10.0
    assert report.summary == ""
    assert len(report.sections) == 1
    assert report.sections[0].name == "Metrics"
    assert report.sections[0].score == 0.0
    assert report.sections[0].issues == ["Missing target"]
    assert report.sections[0].suggestions == []
    assert report.sections[0].rationale == ""
    assert report.sections[0].action_items == ["Define a target"]


def test_validator_extracts_first_json_object_without_greedy_matching():
    response = (
        'Analysis: {"overall_score": 8, "summary": "Useful", "sections": []} '
        'Trailing example: {"ignored": true}'
    )

    report = PRDValidator(
        ai_client=FakeAIClientForValidator(response=response)
    ).validate(SAMPLE_PRD)

    assert report.is_valid is True
    assert report.overall_score == 8.0
    assert report.summary == "Useful"


def test_validator_localizes_invalid_response_message():
    report = PRDValidator(
        ai_client=FakeAIClientForValidator(response="resposta inválida"),
        lang="pt-BR",
    ).validate(SAMPLE_PRD)

    assert report.is_valid is False
    assert "Não foi possível" in report.summary


def test_local_validator_falls_back_to_nonzero_structural_score():
    report = PRDValidator(
        ai_client=IncompleteLocalAIClient(response='{"overall_score": 0}'),
        lang="pt-BR",
    ).validate(
        """
# PRD
## Problema
Alertas chegam tarde.
## Objetivos
Reduzir o tempo de resposta em 30%.
## Escopo
Alertas e histórico.
## Fora do escopo
Compras automáticas.
## Requisitos
- Emitir alerta em até 5 min.
## Métricas
P95 menor que 5 min.
## Riscos
Fadiga de alertas; monitorar taxa de abertura.
"""
        + ("Contexto adicional. " * 20)
    )

    assert report.is_valid is True
    assert report.overall_score > 0
    assert len(report.sections) == 6
    assert "nota conservadora" in report.summary
