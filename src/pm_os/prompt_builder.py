class PromptBuilder:
    """
    Builds prompts for PM OS workflows.

    Public API:
    - build(workflow_name, context)

    For now, only create_prd is supported.
    """

    def build(self, workflow_name: str, context: str) -> str:
        if workflow_name == "create_prd":
            return self._build_create_prd_prompt(context)

        raise ValueError(f"Unsupported workflow: {workflow_name}")

    def _build_create_prd_prompt(self, context: str) -> str:
        return f"""
Você é uma Product Manager experiente.

Crie um PRD completo em Markdown com base no contexto abaixo.

O PRD deve conter:

1. Visão geral
2. Problema
3. Objetivos
4. Fora de escopo
5. Personas / usuários
6. Requisitos funcionais
7. Requisitos não funcionais
8. Métricas de sucesso
9. Riscos
10. Perguntas em aberto

Contexto:

{context}
"""