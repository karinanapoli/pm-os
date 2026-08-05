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
        if "Gerador de Backlog" in prompt or "Backlog Generator" in prompt:
            return """## Iniciativa: Demonstração de backlog

**Objetivo de negócio:** Demonstrar a estrutura de backlog do PM Studio.

**Alinhamento estratégico:** A definir

**Métricas de sucesso**

| Métrica | Baseline atual | Meta | Prazo |
|---|---|---|---|
| Compreensão da estrutura | A definir | A definir | A definir |

**Squads envolvidos:** A definir

**Horizonte temporal:** A definir

**Épicos que compõem esta iniciativa**

- [ ] Estruturação inicial

**Fora do escopo desta iniciativa**

- Interpretar dados reais no modo Demo

**Riscos e dependências macro**

- A definir

**Status:** [x] Em discovery  [ ] Aprovada  [ ] Em desenvolvimento  [ ] Concluída

## Épico: Estruturação inicial

**Iniciativa pai:** Demonstração de backlog

**Squad responsável:** A definir | **PM:** A definir | **Tech Lead:** A definir | **Designer:** A definir

**Problema que resolve:** Torna visível o formato esperado para um backlog.

**Descrição:** Exibe uma amostra revisável da hierarquia de trabalho.

**Critério de conclusão do épico — Definition of Done**

- A estrutura pode ser visualizada e baixada em Markdown.

**Métricas de acompanhamento:** A definir

**Estimativa macro:** [x] P  [ ] M  [ ] G

**Dependências:** Nenhuma identificada

**Histórias que compõem este épico**

- [ ] Visualizar estrutura demonstrativa

**Status:** [x] Em refinamento  [ ] Pronto para dev  [ ] Em desenvolvimento  [ ] Concluído

### História: Visualizar estrutura demonstrativa

**Épico pai:** Estruturação inicial

**Tipo:** [x] User Story  [ ] Technical Story  [ ] Job Story

> Como PM, quero visualizar um backlog estruturado, para que eu possa entender o formato antes de usar um provedor de IA.

**Contexto e motivação:** Demonstrar o fluxo sem enviar dados a uma IA externa.

**Critérios de aceite**

1. O arquivo começa com uma iniciativa.
2. O arquivo contém ao menos um épico relacionado à iniciativa.
3. O arquivo contém ao menos uma história relacionada ao épico.

**Fora do escopo desta história**

- Interpretar documentos da iniciativa

**Notas de design:** A definir

**Notas técnicas:** A definir

**Prioridade:** [ ] P0 — crítico  [x] P1  [ ] P2 | **Esforço:** [x] P  [ ] M  [ ] G

**Dependências:** Nenhuma identificada | **Requer spike?** [ ] Sim  [x] Não
"""
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
