import os

import httpx

from pm_os.contracts.workflow_contracts import AIProviderError


class AnthropicClient:
    def __init__(
        self,
        model: str = "",
        api_key: str = "",
        base_url: str = "",
    ):
        self.model = model or os.getenv("PM_OS_ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = (base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")).rstrip("/")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise AIProviderError("Anthropic API key not configured. Set it in Settings or ANTHROPIC_API_KEY env var.")

        try:
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
            blocks = data.get("content") if isinstance(data, dict) else None
            if not isinstance(blocks, list):
                raise AIProviderError("Anthropic returned no generated content.")
            text_blocks = [
                block.get("text")
                for block in blocks
                if isinstance(block, dict)
                and isinstance(block.get("text"), str)
                and block["text"].strip()
            ]
            if not text_blocks:
                raise AIProviderError("Anthropic returned no generated content.")
            return "\n".join(text_blocks)
        except httpx.HTTPStatusError as e:
            raise AIProviderError(f"Anthropic API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise AIProviderError(f"Anthropic request failed: {e}") from e
        except (ValueError, TypeError) as e:
            raise AIProviderError("Anthropic returned an invalid response.") from e
