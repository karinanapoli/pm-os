from dataclasses import asdict, dataclass
from typing import Callable, Optional

from pm_os.citation_verifier import extract_source_ids, verify_citations
from pm_os.context_builder import ContextBuilder
from pm_os.contracts.workflow_contracts import AIClient
from pm_os.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class ProductConsultationResult:
    answer: str
    initiatives: list[str]
    references: list[dict]
    mcp_used: list[str]
    citation_report: dict

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "initiatives": self.initiatives,
            "references": self.references,
            "mcp_used": self.mcp_used,
            "citation_report": self.citation_report,
        }


class ProductConsultationService:
    """Answer product questions using the explicitly selected context."""

    def __init__(
        self,
        ai_client: AIClient,
        initiative_repository,
        product_docs_context_loader: Callable[[], str],
        mcp_context_loader: Callable[[], list[dict]],
    ):
        self.ai_client = ai_client
        self.initiative_repository = initiative_repository
        self.product_docs_context_loader = product_docs_context_loader
        self.mcp_context_loader = mcp_context_loader

    def consult(
        self,
        question: str,
        initiative_names: list[str],
        use_product_docs: bool,
        use_mcp: bool,
        lang: str = "en",
        conversation: Optional[list[dict]] = None,
    ) -> ProductConsultationResult:
        context_parts = []
        for name in initiative_names:
            initiative = self.initiative_repository.get(name)
            if initiative and initiative.documents:
                content = ContextBuilder().build(initiative)
                context_parts.append(
                    f"--- Iniciativa: {initiative.name} ---\n\n{content}"
                )

        product_docs_used = False
        if use_product_docs:
            content = self.product_docs_context_loader()
            if content.strip():
                context_parts.append(
                    f"--- Documentação complementar ---\n\n{content}"
                )
                product_docs_used = True

        used_mcp = []
        if use_mcp:
            for item in self.mcp_context_loader():
                context_parts.append(
                    f"--- Contexto MCP: {item['name']} ---\n\n{item['content']}"
                )
                used_mcp.append(item["name"])

        recent_messages = [
            item for item in (conversation or [])[-6:]
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]
        if recent_messages:
            transcript = "\n".join(
                f"{item['role']}: {str(item['content'])[:2000]}"
                for item in recent_messages
            )
            context_parts.append(f"--- Conversa anterior ---\n\n{transcript}")

        context = (
            "\n\n".join(context_parts)
            if context_parts
            else "Nenhum documento disponível."
        )
        prompt = PromptBuilder().build("consult", context, question, lang=lang)
        answer = self.ai_client.generate(prompt)
        citations = verify_citations(answer, extract_source_ids(context))

        references = [
            {"initiative": name}
            for name in initiative_names
            if name in answer
        ]
        if product_docs_used and (
            "Documentação complementar" in answer
            or "produto" in answer.lower()
        ):
            references.append({"initiative": "Documentação complementar"})
        references.extend(
            {"initiative": name}
            for name in used_mcp
            if name.lower() in answer.lower()
        )
        sources = initiative_names.copy()
        if product_docs_used:
            sources.append("Documentação complementar")
        sources.extend(used_mcp)

        return ProductConsultationResult(
            answer=answer,
            initiatives=sources,
            references=references,
            mcp_used=used_mcp,
            citation_report=asdict(citations),
        )
