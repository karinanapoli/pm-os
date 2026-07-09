class FakeAIClient:
    """
    Fake AI client used to validate the workflow without calling a real LLM.
    """

    def generate(self, prompt: str) -> str:
        return f"""
# Product Requirement Document

Este é um PRD gerado pelo Fake AI Client.

Quando integrarmos o Ollama,
o resultado deste método virá do modelo.

Tamanho do prompt recebido:

{len(prompt)} caracteres.
"""