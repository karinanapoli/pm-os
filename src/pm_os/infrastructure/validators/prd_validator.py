import json
import math
import re
from typing import Any

from pm_os.contracts.workflow_contracts import AIClient
from pm_os.domain.validation_report import SectionEvaluation, ValidationReport


class PRDValidator:
    """
    Validates a PRD using an AI model.

    Evaluates structure, metric quality, risk completeness,
    scope clarity, and overall coherence.
    """

    def __init__(self, ai_client: AIClient, lang: str = "en"):
        self.ai_client = ai_client
        self.lang = lang

    def validate(self, prd_content: str) -> ValidationReport:
        prompt = self._build_prompt(prd_content)
        limited_generate = getattr(self.ai_client, "generate_with_limit", None)
        response = (
            limited_generate(prompt, 640)
            if callable(limited_generate)
            else self.ai_client.generate(prompt)
        )
        return self._parse_response(response)

    def _build_prompt(self, prd_content: str) -> str:
        if self.lang == "pt-BR":
            return self._build_prompt_ptbr(prd_content)
        return self._build_prompt_en(prd_content)

    def _build_prompt_en(self, prd_content: str) -> str:
        return f"""
You are a Product Management quality analyst.

Evaluate the following PRD and return a JSON object with:

- "overall_score": a float from 0 to 10
- "summary": a short paragraph summarizing the PRD quality
- "sections": a list of objects, each with:
  - "name": section name (e.g. "Metrics", "Risks", "Scope", "Requirements")
  - "score": float from 0 to 10
  - "rationale": one concise sentence explaining WHY this section received this score
  - "issues": up to 2 strings describing the most important problems found
  - "action_items": up to 2 concrete, prescriptive next steps the PM should take
  - "suggestions": up to 1 string with a general improvement idea

Evaluation criteria:
- **Metrics**: Are they specific, measurable, achievable, relevant, time-bound (SMART)?
- **Risks**: Do they have mitigation plans, or are they just generic fears?
- **Scope**: Is the scope well-defined? Any contradictions (e.g. something listed as "out of scope" but required elsewhere)?
- **Requirements**: Are they specific, unambiguous, and testable?
- **Structure**: Are all required sections present and well-organized?
- **Coherence**: Does the PRD tell a consistent story from problem to solution?

Return exactly these 6 sections: Metrics, Risks, Scope, Requirements, Structure, Coherence.
Keep the complete response concise (under 600 tokens).

Return ONLY valid JSON inside a ```json code block.

PRD Content:

{prd_content}
"""

    def _build_prompt_ptbr(self, prd_content: str) -> str:
        return f"""
Você é um analista de qualidade de Product Management.

Avalie o PRD abaixo e retorne um objeto JSON com:

- "overall_score": um número float de 0 a 10
- "summary": um parágrafo curto resumindo a qualidade do PRD
- "sections": uma lista de objetos, cada um com:
  - "name": nome da seção (ex: "Métricas", "Riscos", "Escopo", "Requisitos")
  - "score": float de 0 a 10
  - "rationale": uma frase concisa explicando POR QUE esta seção recebeu esta nota
  - "issues": até 2 strings descrevendo os problemas mais importantes
  - "action_items": até 2 próximos passos concretos e prescritivos
  - "suggestions": até 1 string com uma ideia geral de melhoria

Critérios de avaliação:
- **Métricas**: São específicas, mensuráveis, atingíveis, relevantes e com prazo (SMART)?
- **Riscos**: Possuem planos de mitigação ou são apenas medos genéricos?
- **Escopo**: O escopo está bem definido? Há contradições (ex: algo listado como "fora do escopo" mas exigido em outro lugar)?
- **Requisitos**: São específicos, inequívocos e testáveis?
- **Estrutura**: Todas as seções necessárias estão presentes e bem organizadas?
- **Coerência**: O PRD conta uma história consistente do problema à solução?

Retorne exatamente estas 6 seções: Métricas, Riscos, Escopo, Requisitos, Estrutura e Coerência.
Mantenha a resposta completa concisa (menos de 600 tokens).

IMPORTANTE: Responda EM PORTUGUÊS. Todos os campos de texto (summary, rationale, issues, action_items, suggestions) devem estar em português brasileiro.

Retorne APENAS JSON válido dentro de um bloco de código ```json.

Conteúdo do PRD:

{prd_content}
"""

    def _parse_response(self, response: str) -> ValidationReport:
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        else:
            raw = response[response.find("{"):] if "{" in response else ""

        try:
            data, _ = json.JSONDecoder().raw_decode(raw.strip())
        except (json.JSONDecodeError, TypeError):
            return self._invalid_report()

        if not isinstance(data, dict):
            return self._invalid_report()

        raw_sections = data.get("sections", [])
        if not isinstance(raw_sections, list):
            raw_sections = []

        sections = []
        for raw_section in raw_sections[:20]:
            if not isinstance(raw_section, dict):
                continue
            sections.append(
                SectionEvaluation(
                    name=self._text(raw_section.get("name"), "Unknown"),
                    score=self._score(raw_section.get("score")),
                    issues=self._text_list(raw_section.get("issues")),
                    suggestions=self._text_list(raw_section.get("suggestions")),
                    rationale=self._text(raw_section.get("rationale")),
                    action_items=self._text_list(raw_section.get("action_items")),
                )
            )

        return ValidationReport(
            overall_score=self._score(data.get("overall_score")),
            summary=self._text(data.get("summary")),
            sections=sections,
        )

    def _invalid_report(self) -> ValidationReport:
        summary = (
            "Não foi possível interpretar a resposta da IA. Tente validar novamente."
            if self.lang == "pt-BR"
            else "Could not parse the AI validation response. Please try again."
        )
        return ValidationReport(
            overall_score=0.0,
            summary=summary,
            sections=[],
            is_valid=False,
        )

    @staticmethod
    def _score(value: Any) -> float:
        if isinstance(value, bool):
            return 0.0
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(score):
            return 0.0
        return min(10.0, max(0.0, score))

    @staticmethod
    def _text(value: Any, default: str = "") -> str:
        if not isinstance(value, str):
            return default
        return value.strip()[:4000]

    @classmethod
    def _text_list(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            text
            for item in value[:50]
            if (text := cls._text(item)[:1000])
        ]
