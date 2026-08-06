from pm_os.web.initiative_chat_service import InitiativeChatService


def test_chat_history_persists_exchange_and_can_be_cleared(tmp_path):
    service = InitiativeChatService()

    messages = service.append_exchange(
        tmp_path,
        question="Quais são os riscos?",
        answer="O principal risco é a qualidade dos dados.",
        actor="pm@example.com",
        sources=["INT-001", "Analytics"],
        mcp_used=["Analytics"],
    )

    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert service.load(tmp_path)[1]["mcp_used"] == ["Analytics"]
    service.clear(tmp_path)
    assert service.load(tmp_path) == []
