class FakeAIClient:
    """
    Fake AI client used to validate the workflow without calling a real LLM.
    """

    def generate(self, prompt: str) -> str:
        if "Avalie a qualidade" in prompt or "Evaluate the quality" in prompt:
            return """```json
{"overall_score": 7.5, "sections": [
  {"name": "Demo", "score": 7.5, "issues": [], "suggestions": ["Conecte um provedor de IA para uma avaliação contextual."], "rationale": "Resultado demonstrativo.", "action_items": []}
]}
```"""
        return f"""# PRD demonstrativo

> Este documento foi criado no modo Demo. Nenhum conteúdo foi enviado para uma IA externa.

## Visão geral

Exemplo de como o PM Studio transforma contexto em um artefato estruturado.

## Problema

Informações de produto ficam dispersas e difíceis de reutilizar.

## Objetivos

- Centralizar o contexto de uma iniciativa.
- Tornar decisões e perguntas em aberto visíveis.
- Demonstrar o fluxo completo sem exigir chave de API.

## Fora do escopo

- Substituir a análise crítica da pessoa responsável pelo produto.

## Requisitos

1. Manter documentos de contexto organizados por iniciativa.
2. Gerar artefatos revisáveis.
3. Informar claramente quando o resultado for demonstrativo.

## Métricas de sucesso

- Primeira iniciativa criada em menos de cinco minutos.
- Usuário entende a diferença entre contexto, prompt e resultado.

## Riscos

- O conteúdo deste modo é ilustrativo e não interpreta o contexto enviado.

## Perguntas em aberto

- Qual provedor e modelo são adequados ao nível de privacidade desejado?

_Tamanho do prompt demonstrado: {len(prompt)} caracteres._
"""
