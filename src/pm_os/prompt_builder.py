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
