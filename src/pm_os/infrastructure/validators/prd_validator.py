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
        response = self.ai_client.generate(prompt)
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
  - "rationale": a 2-3 sentence explanation of WHY this section received this score (what's missing, what's good, what's unclear)
  - "issues": list of strings describing specific problems found
  - "action_items": list of concrete, prescriptive next steps the PM should take (e.g. "Interview stakeholder X to validate requirements", "Add success metrics for feature Y", "Analyze the impact of decision Z on the schedule", "Document the dependency with team A"). Each item must be a specific action, not generic advice.
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

    def _build_prompt_ptbr(self, prd_content: str) -> str:
        return f"""
Você é um analista de qualidade de Product Management.

Avalie o PRD abaixo e retorne um objeto JSON com:

- "overall_score": um número float de 0 a 10
- "summary": um parágrafo curto resumindo a qualidade do PRD
- "sections": uma lista de objetos, cada um com:
  - "name": nome da seção (ex: "Métricas", "Riscos", "Escopo", "Requisitos")
  - "score": float de 0 a 10
  - "rationale": explicação de 2 a 3 frases do POR QUE esta seção recebeu esta nota (o que está faltando, o que está bom, o que não está claro)
  - "issues": lista de strings descrevendo problemas específicos encontrados
  - "action_items": lista de próximos passos concretos e prescritivos que o PM deve tomar (ex: "Entreviste o stakeholder X para validar os requisitos", "Adicione métricas de sucesso para a funcionalidade Y", "Analise o impacto da decisão Z no cronograma", "Documente a dependência com o time A"). Cada item deve ser uma ação específica, não um conselho genérico.
  - "suggestions": lista de strings com ideias gerais de melhoria

Critérios de avaliação:
- **Métricas**: São específicas, mensuráveis, atingíveis, relevantes e com prazo (SMART)?
- **Riscos**: Possuem planos de mitigação ou são apenas medos genéricos?
- **Escopo**: O escopo está bem definido? Há contradições (ex: algo listado como "fora do escopo" mas exigido em outro lugar)?
- **Requisitos**: São específicos, inequívocos e testáveis?
- **Estrutura**: Todas as seções necessárias estão presentes e bem organizadas?
- **Coerência**: O PRD conta uma história consistente do problema à solução?

Para cada seção, explique o rationale da nota e forneça 2 a 3 itens de ação específicos que o PM pode executar imediatamente.

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
