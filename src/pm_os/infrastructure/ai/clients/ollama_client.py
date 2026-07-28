import http.client
import json
import os
import urllib.error
import urllib.request


class OllamaConnectionError(RuntimeError):
    """
    Raised when PM OS cannot connect to the local Ollama server.
    """

    def __init__(self, message: str = "Could not connect to the Ollama server."):
        super().__init__(message)


class OllamaResponseError(OllamaConnectionError):
    def __init__(self):
        super().__init__("Ollama returned an invalid or empty response.")


class OllamaClient:
    """
    AI client that connects PM OS to a local Ollama server.

    Model can be overridden via the PM_OS_MODEL environment variable.
    """

    def __init__(
        self,
        model: str = "",
        base_url: str = "",
        max_tokens: int = 0,
    ):
        self.model = model or os.getenv("PM_OS_MODEL", "llama3.2")
        self.base_url = (base_url or os.getenv("PM_OS_OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        configured_max = max_tokens or int(os.getenv("PM_OS_OLLAMA_MAX_TOKENS", "1024"))
        self.max_tokens = max(128, configured_max)

    def generate(self, prompt: str) -> str:
        return self.generate_with_limit(prompt, self.max_tokens)

    def generate_with_limit(self, prompt: str, max_tokens: int) -> str:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max(128, max_tokens)},
        }

        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=600,
            ) as response:
                response_body = response.read().decode("utf-8")

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            http.client.RemoteDisconnected,
        ) as error:
            raise OllamaConnectionError() from error

        try:
            data = json.loads(response_body)
            content = data.get("response") if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise OllamaResponseError() from error
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError()
        return content
