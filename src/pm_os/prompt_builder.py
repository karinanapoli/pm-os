class PromptBuilder:
    def build(self, workflow_name: str, context: str, question: str = "") -> str:
        if workflow_name == "create_prd":
            return self._build_create_prd_prompt(context)
        if workflow_name == "consult":
            return self._build_consult_prompt(context, question)
        raise ValueError(f"Unsupported workflow: {workflow_name}")

    def _build_create_prd_prompt(self, context: str) -> str:
        return f"""
You are an experienced Product Manager.

Create a complete PRD in Markdown based on the context below.

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
Cite a fonte (iniciativa ou documentação do produto) de onde cada informação foi extraída.

Pergunta: {question}"""
