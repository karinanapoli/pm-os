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

Retorne APENAS JSON válido dentro de um bloco de código ```json.

Conteúdo do PRD:

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
