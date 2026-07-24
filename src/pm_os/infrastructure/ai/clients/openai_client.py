import os

import httpx

from pm_os.contracts.workflow_contracts import AIProviderError


class OpenAIClient:
    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "",
    ):
        self.model = model or os.getenv("PM_OS_OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

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
            choices = data.get("choices") if isinstance(data, dict) else None
            if not isinstance(choices, list) or not choices:
                raise AIProviderError("OpenAI returned no generated content.")
            choice = choices[0] if isinstance(choices[0], dict) else {}
            message = choice.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise AIProviderError("OpenAI returned no generated content.")
            return content
        except httpx.HTTPStatusError as e:
            raise AIProviderError(f"OpenAI API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise AIProviderError(f"OpenAI request failed: {e}") from e
        except (ValueError, TypeError) as e:
            raise AIProviderError("OpenAI returned an invalid response.") from e
