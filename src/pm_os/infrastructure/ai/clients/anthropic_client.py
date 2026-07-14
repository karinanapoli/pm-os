import os

import httpx


class AnthropicClient:
    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "https://api.anthropic.com/v1",
    ):
        self.model = model or os.getenv("PM_OS_ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("Anthropic API key not configured. Set it in Settings or ANTHROPIC_API_KEY env var.")

        resp = httpx.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=600,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
