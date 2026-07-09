from pm_os.models import Feature


class ContextBuilder:
    """
    Responsável por transformar uma Feature em um contexto consolidado
    que poderá ser enviado ao LLM.
    """

    def build(self, feature: Feature) -> str:

        sections = []

        for document in feature.documents:

            content = document.read_text(encoding="utf-8")

            sections.append(
                f"""
# Documento: {document.name}

{content}
"""
            )

        return "\n\n---\n\n".join(sections)