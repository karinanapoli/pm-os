import json
import urllib.error
import urllib.request


class OllamaConnectionError(RuntimeError):
    """
    Raised when PM OS cannot connect to the local Ollama server.
    """

    def __init__(self):
        super().__init__("Could not connect to the Ollama server.")


class OllamaClient:
    """
    AI client that connects PM OS to a local Ollama server.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
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
                timeout=120,
            ) as response:
                response_body = response.read().decode("utf-8")
                data = json.loads(response_body)

        except urllib.error.URLError as error:
            raise OllamaConnectionError() from error

        return data["response"]