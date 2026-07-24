import json
import urllib.error

import httpx
import pytest

from pm_os.contracts.workflow_contracts import AIProviderError
from pm_os.infrastructure.ai.clients.anthropic_client import AnthropicClient
from pm_os.infrastructure.ai.clients.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaResponseError,
)
from pm_os.infrastructure.ai.clients.openai_client import OpenAIClient
from pm_os.infrastructure.ai.clients.gateway_client import GatewayClient


class FakeHTTPResponse:
    def __init__(self, payload=None, status_error=None, json_error=None):
        self.payload = payload
        self.status_error = status_error
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


def test_openai_uses_environment_and_returns_generated_content(monkeypatch):
    captured = {}
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example/v1/")

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeHTTPResponse({"choices": [{"message": {"content": "Generated PRD"}}]})

    monkeypatch.setattr("pm_os.infrastructure.ai.clients.openai_client.httpx.post", fake_post)

    result = OpenAIClient(model="test-model").generate("Product context")

    assert result == "Generated PRD"
    assert captured["url"] == "https://gateway.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer env-key"
    assert captured["json"]["model"] == "test-model"


def test_openai_rejects_missing_key_and_empty_response(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIProviderError, match="key not configured"):
        OpenAIClient().generate("prompt")

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.openai_client.httpx.post",
        lambda *args, **kwargs: FakeHTTPResponse({"choices": []}),
    )
    with pytest.raises(AIProviderError, match="no generated content"):
        OpenAIClient(api_key="key").generate("prompt")


def test_openai_normalizes_http_network_and_invalid_json_errors(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    status_error = httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.openai_client.httpx.post",
        lambda *args, **kwargs: FakeHTTPResponse(status_error=status_error),
    )
    with pytest.raises(AIProviderError, match="429"):
        OpenAIClient(api_key="key").generate("prompt")

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.openai_client.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("offline", request=request)),
    )
    with pytest.raises(AIProviderError, match="request failed"):
        OpenAIClient(api_key="key").generate("prompt")

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.openai_client.httpx.post",
        lambda *args, **kwargs: FakeHTTPResponse(json_error=ValueError("bad json")),
    )
    with pytest.raises(AIProviderError, match="invalid response"):
        OpenAIClient(api_key="key").generate("prompt")


def test_anthropic_uses_environment_and_joins_text_blocks(monkeypatch):
    captured = {}
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example/anthropic/")

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeHTTPResponse(
            {"content": [{"type": "text", "text": "First"}, {"type": "text", "text": "Second"}]}
        )

    monkeypatch.setattr("pm_os.infrastructure.ai.clients.anthropic_client.httpx.post", fake_post)

    result = AnthropicClient(model="claude-test").generate("Product context")

    assert result == "First\nSecond"
    assert captured["url"] == "https://gateway.example/anthropic/messages"
    assert captured["headers"]["x-api-key"] == "anthropic-key"
    assert captured["json"]["model"] == "claude-test"


def test_anthropic_rejects_missing_key_and_empty_response(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AIProviderError, match="key not configured"):
        AnthropicClient().generate("prompt")

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.anthropic_client.httpx.post",
        lambda *args, **kwargs: FakeHTTPResponse({"content": [{"type": "tool_use"}]}),
    )
    with pytest.raises(AIProviderError, match="no generated content"):
        AnthropicClient(api_key="key").generate("prompt")


def test_gateway_sends_routing_metadata_and_returns_content(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeHTTPResponse({
            "choices": [{"message": {"content": "Gateway PRD"}}]
        })

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.gateway_client.httpx.post",
        fake_post,
    )
    client = GatewayClient(
        base_url="https://gateway.example/v1/",
        provider="openai",
        project_id="pm-studio",
        identifier="gpt-4o-mini-prod",
        api_key="gateway-key",
    )

    assert client.generate("Product context") == "Gateway PRD"
    assert captured["url"] == (
        "https://gateway.example/v1/chat/completions"
    )
    assert captured["headers"]["X-Gateway-Provider"] == "openai"
    assert captured["headers"]["X-Project-Id"] == "pm-studio"
    assert captured["headers"]["X-Identifier"] == "gpt-4o-mini-prod"
    assert captured["headers"]["Authorization"] == "Bearer gateway-key"
    assert captured["json"]["model"] == "gpt-4o-mini-prod"


def test_gateway_requires_complete_routing_configuration():
    with pytest.raises(
        AIProviderError,
        match="Gateway configuration incomplete",
    ):
        GatewayClient(base_url="https://gateway.example/v1").generate(
            "prompt"
        )


def test_gateway_explains_authentication_and_timeout_errors(monkeypatch):
    request = httpx.Request(
        "POST",
        "https://gateway.example/v1/chat/completions",
    )
    response = httpx.Response(401, request=request)
    status_error = httpx.HTTPStatusError(
        "unauthorized",
        request=request,
        response=response,
    )
    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.gateway_client.httpx.post",
        lambda *args, **kwargs: FakeHTTPResponse(
            status_error=status_error
        ),
    )
    client = GatewayClient(
        base_url="https://gateway.example/v1",
        provider="openai",
        project_id="pm-studio",
        identifier="gpt-prod",
    )
    with pytest.raises(AIProviderError, match="credentials were rejected"):
        client.generate("prompt")

    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.gateway_client.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            httpx.ReadTimeout("slow", request=request)
        ),
    )
    with pytest.raises(AIProviderError, match="before the timeout"):
        client.generate("prompt")


class FakeOllamaResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


def test_ollama_uses_environment_and_returns_content(monkeypatch):
    captured = {}
    monkeypatch.setenv("PM_OS_MODEL", "local-model")
    monkeypatch.setenv("PM_OS_OLLAMA_URL", "http://ollama.example/")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeOllamaResponse(b'{"response": "Local PRD"}')

    monkeypatch.setattr("pm_os.infrastructure.ai.clients.ollama_client.urllib.request.urlopen", fake_urlopen)

    result = OllamaClient().generate("Product context")

    assert result == "Local PRD"
    assert captured["url"] == "http://ollama.example/api/generate"
    assert captured["payload"]["model"] == "local-model"


@pytest.mark.parametrize(
    "payload",
    [b"not json", b"{}", b'{"response": ""}'],
)
def test_ollama_rejects_invalid_or_empty_responses(monkeypatch, payload):
    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.ollama_client.urllib.request.urlopen",
        lambda *args, **kwargs: FakeOllamaResponse(payload),
    )
    with pytest.raises(OllamaResponseError):
        OllamaClient().generate("prompt")


def test_ollama_normalizes_network_errors(monkeypatch):
    monkeypatch.setattr(
        "pm_os.infrastructure.ai.clients.ollama_client.urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )
    with pytest.raises(OllamaConnectionError, match="Could not connect"):
        OllamaClient().generate("prompt")
