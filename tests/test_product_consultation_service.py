from pathlib import Path

from pm_os.domain.initiative import Initiative
from pm_os.web.product_consultation_service import ProductConsultationService


class FakeAIClient:
    def __init__(self, answer):
        self.answer = answer
        self.prompt = ""

    def generate(self, prompt):
        self.prompt = prompt
        return self.answer


class FakeRepository:
    def __init__(self, initiatives):
        self.initiatives = {item.name: item for item in initiatives}

    def get(self, name):
        return self.initiatives.get(name)


def test_consultation_combines_selected_sources_and_references():
    ai = FakeAIClient("Growth and Analytics support the produto decision.")
    repository = FakeRepository([
        Initiative("Growth", Path("/growth"), documents=["Retention data"])
    ])
    service = ProductConsultationService(
        ai_client=ai,
        initiative_repository=repository,
        product_docs_context_loader=lambda: "Product strategy",
        mcp_context_loader=lambda: [
            {"name": "Analytics", "content": "Conversion: 12%"}
        ],
    )

    result = service.consult(
        question="What should we prioritize?",
        initiative_names=["Growth"],
        use_product_docs=True,
        use_mcp=True,
        lang="pt-BR",
    )

    assert "Retention data" in ai.prompt
    assert "Product strategy" in ai.prompt
    assert "Conversion: 12%" in ai.prompt
    assert result.initiatives == [
        "Growth",
        "Documentação complementar",
        "Analytics",
    ]
    assert result.references == [
        {"initiative": "Growth"},
        {"initiative": "Documentação complementar"},
        {"initiative": "Analytics"},
    ]
    assert result.to_dict()["answer"] == ai.answer


def test_consultation_ignores_unavailable_optional_context():
    ai = FakeAIClient("No evidence available.")
    service = ProductConsultationService(
        ai_client=ai,
        initiative_repository=FakeRepository([]),
        product_docs_context_loader=lambda: "",
        mcp_context_loader=lambda: [],
    )

    result = service.consult(
        question="What do we know?",
        initiative_names=["Missing"],
        use_product_docs=True,
        use_mcp=False,
    )

    assert "Nenhum documento disponível." in ai.prompt
    assert result.initiatives == ["Missing"]
    assert result.references == []


def test_consultation_includes_recent_chat_messages_as_context():
    ai = FakeAIClient("Follow-up answer")
    service = ProductConsultationService(
        ai_client=ai,
        initiative_repository=FakeRepository([]),
        product_docs_context_loader=lambda: "",
        mcp_context_loader=lambda: [],
    )

    service.consult(
        question="And what is the main risk?",
        initiative_names=[],
        use_product_docs=False,
        use_mcp=False,
        conversation=[
            {"role": "user", "content": "Summarize the initiative"},
            {"role": "assistant", "content": "The initiative improves supplier search."},
        ],
    )

    assert "Conversa anterior" in ai.prompt
    assert "The initiative improves supplier search." in ai.prompt
