import json
import re

from pm_os.contracts.workflow_contracts import AIClient
from pm_os.domain.validation_report import SectionEvaluation, ValidationReport


class PRDValidator:
    """
    Validates a PRD using an AI model.

    Evaluates structure, metric quality, risk completeness,
    scope clarity, and overall coherence.
    """

    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def validate(self, prd_content: str) -> ValidationReport:
        prompt = self._build_prompt(prd_content)
        response = self.ai_client.generate(prompt)
        return self._parse_response(response)

    def _build_prompt(self, prd_content: str) -> str:
        return f"""
You are a Product Management quality analyst.

Evaluate the following PRD and return a JSON object with:

- "overall_score": a float from 0 to 10
- "summary": a short paragraph summarizing the PRD quality
- "sections": a list of objects, each with:
  - "name": section name (e.g. "Metrics", "Risks", "Scope", "Requirements")
  - "score": float from 0 to 10
  - "rationale": a 2-3 sentence explanation of WHY this section received this score (what's missing, what's good, what's unclear)
  - "issues": list of strings describing specific problems found
  - "action_items": list of concrete, prescriptive next steps the PM should take (e.g. "Entreviste o stakeholder X para validar os requisitos", "Adicione métricas de sucesso para a funcionalidade Y", "Analise o impacto da decisão Z no cronograma", "Documente a dependência com o time A"). Each item must be a specific action, not generic advice.
  - "suggestions": list of strings with general improvement ideas

Evaluation criteria:
- **Metrics**: Are they specific, measurable, achievable, relevant, time-bound (SMART)?
- **Risks**: Do they have mitigation plans, or are they just generic fears?
- **Scope**: Is the scope well-defined? Any contradictions (e.g. something listed as "out of scope" but required elsewhere)?
- **Requirements**: Are they specific, unambiguous, and testable?
- **Structure**: Are all required sections present and well-organized?
- **Coherence**: Does the PRD tell a consistent story from problem to solution?

For each section, explain the score rationale and provide 2-3 specific action items the PM can execute immediately.

Return ONLY valid JSON inside a ```json code block.

PRD Content:

{prd_content}
"""

    def _parse_response(self, response: str) -> ValidationReport:
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
        if not json_match:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)

        if not json_match:
            return ValidationReport(
                overall_score=0.0,
                summary="Could not parse validation response.",
                sections=[],
            )

        raw = json_match.group(1) if "```" in response else json_match.group(0)

        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            return ValidationReport(
                overall_score=0.0,
                summary="Invalid JSON in validation response.",
                sections=[],
            )

        sections = [
            SectionEvaluation(
                name=s.get("name", "Unknown"),
                score=s.get("score", 0.0),
                issues=s.get("issues", []),
                suggestions=s.get("suggestions", []),
                rationale=s.get("rationale", ""),
                action_items=s.get("action_items", []),
            )
            for s in data.get("sections", [])
        ]

        return ValidationReport(
            overall_score=data.get("overall_score", 0.0),
            summary=data.get("summary", ""),
            sections=sections,
        )
