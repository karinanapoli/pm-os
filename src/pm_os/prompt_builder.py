class PromptBuilder:
    def build(self, workflow_name: str, context: str, question: str = "", lang: str = "en") -> str:
        if workflow_name == "create_prd":
            return self._build_create_prd_prompt(context, lang)
        if workflow_name == "create_specification":
            return self._build_create_specification_prompt(context, lang)
        if workflow_name == "consult":
            if lang == "en":
                return self._build_consult_prompt_en(context, question)
            return self._build_consult_prompt(context, question)
        raise ValueError(f"Unsupported workflow: {workflow_name}")

    def _build_create_specification_prompt(self, context: str, lang: str = "en") -> str:
        fields = (
            "problem, users, evidence, outcome, metrics, scope, out_of_scope, "
            "requirements, constraints, risks, dependencies, hypotheses, "
            "open_questions, acceptance_criteria"
        )
        if lang == "pt-BR":
            return f"""
Você é uma Product Manager experiente preparando uma especificação revisável.

Analise SOMENTE o contexto fornecido e retorne um objeto JSON válido, sem texto
antes ou depois. Use exatamente estas chaves:

{fields}

Regras:

- Preserve identificadores de fonte no formato [SRC-XXXXXXXX].
- Não invente fatos, métricas, requisitos ou fontes.
- Coloque inferências em "hypotheses".
- Coloque informações ausentes ou ambíguas em "open_questions".
- Use strings Markdown; listas devem ter um item por linha.
- Deixe o campo vazio quando o contexto não sustentar uma resposta.

Contexto:

{context}
"""
        return f"""
You are an experienced Product Manager preparing a reviewable specification.

Analyze ONLY the provided context and return a valid JSON object with no text
before or after it. Use exactly these keys:

{fields}

Rules:

- Preserve source identifiers in the [SRC-XXXXXXXX] format.
- Do not invent facts, metrics, requirements, or sources.
- Put inferences in "hypotheses".
- Put missing or ambiguous information in "open_questions".
- Use Markdown strings; lists must have one item per line.
- Leave a field empty when context does not support an answer.

Context:

{context}
"""

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
