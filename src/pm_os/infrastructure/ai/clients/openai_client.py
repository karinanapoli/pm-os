import os

import httpx


class AIProviderError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.model = model or os.getenv("PM_OS_OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise AIProviderError("OpenAI API key not configured. Set it in Settings or OPENAI_API_KEY env var.")

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
                timeout=600,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            return choices[0].get("message", {}).get("content", "")
        except httpx.HTTPStatusError as e:
            raise AIProviderError(f"OpenAI API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise AIProviderError(f"OpenAI request failed: {e}") from e
