class PromptBuilder:
    def build(self, workflow_name: str, context: str, question: str = "", lang: str = "en") -> str:
        if workflow_name == "create_prd":
            return self._build_create_prd_prompt(context, lang)
        if workflow_name == "consult":
            if lang == "en":
                return self._build_consult_prompt_en(context, question)
            return self._build_consult_prompt(context, question)
        raise ValueError(f"Unsupported workflow: {workflow_name}")

    def _build_create_prd_prompt(self, context: str, lang: str = "en") -> str:
        if lang == "pt-BR":
            return f"""
Você é um Product Manager experiente.

Crie um PRD completo em Markdown com base no contexto abaixo.

Regras de evidência:

- Para cada afirmação factual, cite uma ou mais fontes usando o identificador
  exato no formato [SRC-XXXXXXXX].
- Nunca invente uma fonte.
- Separe explicitamente "Fatos sustentados pelas fontes", "Inferências" e
  "Recomendações".
- Quando não houver evidência suficiente, registre a informação em
  "Perguntas em aberto".

O PRD deve incluir:

1. Visão Geral
2. Problema
3. Objetivos
4. Fora do escopo
5. Personas / usuários
6. Requisitos funcionais
7. Requisitos não funcionais
8. Métricas de sucesso
9. Riscos
10. Perguntas em aberto

Contexto:

{context}
"""
        return f"""
You are an experienced Product Manager.

Create a complete PRD in Markdown based on the context below.

Evidence rules:

- Cite every factual claim with one or more exact source identifiers in the
  format [SRC-XXXXXXXX].
- Never invent a source identifier.
- Explicitly separate "Source-backed facts", "Inferences", and
  "Recommendations".
- When evidence is insufficient, add the item to "Open questions".

The PRD must include:

1. Overview
2. Problem
3. Objectives
4. Out of scope
5. Personas / users
6. Functional requirements
7. Non-functional requirements
8. Success metrics
9. Risks
10. Open questions

Context:

{context}
"""

    def _build_consult_prompt(self, context: str, question: str) -> str:
        return f"""Você é um analista de documentação de produto.

Abaixo estão documentos de diversas fontes (iniciativas e/ou documentação do produto).
Cada bloco é precedido por um cabeçalho indicando a origem.

Documentos:
{context}

Com base SOMENTE nos documentos acima, responda à pergunta abaixo.
Se a informação não estiver nos documentos, diga que não encontrou.
Cite cada afirmação factual com o identificador exato [SRC-XXXXXXXX].
Separe fatos sustentados, inferências e recomendações. Nunca invente uma fonte.

Pergunta: {question}"""

    def _build_consult_prompt_en(self, context: str, question: str) -> str:
        return f"""You are a product documentation analyst.

Below are documents from various sources (initiatives and/or product documentation).
Each block is preceded by a header indicating its origin.

Documents:
{context}

Based SOLELY on the documents above, answer the question below.
If the information is not in the documents, say so.
Cite every factual claim with the exact [SRC-XXXXXXXX] identifier.
Separate source-backed facts, inferences, and recommendations. Never invent a source.

Question: {question}"""
