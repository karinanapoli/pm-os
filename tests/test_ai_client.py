from pm_os.infrastructure.ai.clients.fake_ai_client import FakeAIClient


def test_ai_client_generates_fake_prd():
    client = FakeAIClient()

    result = client.generate("Test prompt")

    assert "# Product Requirement Document" in result
    assert "Fake AI Client" in result
    assert "Test prompt" not in result
