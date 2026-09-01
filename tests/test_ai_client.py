from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient


def test_ai_client_generates_fake_prd():
    client = FakeAIClient()

    result = client.generate("Test prompt")

    assert "# PRD demonstrativo" in result
    assert "Nenhum conteúdo foi enviado" in result
    assert "Test prompt" not in result


def test_ai_client_follows_english_prd_language():
    client = FakeAIClient()

    result = client.generate("Create a complete PRD in Markdown")

    assert result.startswith("# Demo PRD")
    assert "## Security by Design" in result
    assert "To be defined" in result
