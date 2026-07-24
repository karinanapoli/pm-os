import os

import httpx

from pm_os.contracts.workflow_contracts import AIProviderError


class GatewayClient:
    """OpenAI-compatible gateway client with explicit routing metadata."""

    def __init__(
        self,
        base_url: str = "",
        provider: str = "",
        project_id: str = "",
        identifier: str = "",
        api_key: str = "",
    ):
        self.base_url = (
            base_url or os.getenv("PM_OS_GATEWAY_URL", "")
        ).rstrip("/")
        self.provider = provider or os.getenv("PM_OS_GATEWAY_PROVIDER", "")
        self.project_id = project_id or os.getenv(
            "PM_OS_GATEWAY_PROJECT_ID", ""
        )
        self.identifier = identifier or os.getenv(
            "PM_OS_GATEWAY_IDENTIFIER", ""
        )
        self.api_key = api_key or os.getenv("PM_OS_GATEWAY_API_KEY", "")

    def generate(self, prompt: str) -> str:
        missing = [
            name
            for name, value in (
                ("URL", self.base_url),
                ("provider", self.provider),
                ("project ID", self.project_id),
                ("identifier", self.identifier),
            )
            if not value
        ]
        if missing:
            raise AIProviderError(
                "Gateway configuration incomplete: "
                + ", ".join(missing)
                + "."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Gateway-Provider": self.provider,
            "X-Project-Id": self.project_id,
            "X-Identifier": self.identifier,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = self.base_url
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"

        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                json={
                    "model": self.identifier,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
                timeout=600,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not isinstance(choices, list) or not choices:
                raise AIProviderError(
                    "Gateway returned no generated content."
                )
            message = (
                choices[0].get("message")
                if isinstance(choices[0], dict)
                else None
            )
            content = (
                message.get("content")
                if isinstance(message, dict)
                else None
            )
            if not isinstance(content, str) or not content.strip():
                raise AIProviderError(
                    "Gateway returned no generated content."
                )
            return content
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(
                f"Gateway API error: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise AIProviderError(
                f"Gateway request failed: {exc}"
            ) from exc
        except (TypeError, ValueError) as exc:
            raise AIProviderError(
                "Gateway returned an invalid response."
            ) from exc
