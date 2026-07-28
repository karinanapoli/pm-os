import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from pm_os.context_builder import ContextBuilder
from pm_os.domain.context_source import ContextSource
from pm_os.web.safe_http import fetch_public_url

_logger = logging.getLogger("pm_os")


class MCPContextService:
    """Fetch enabled MCP contexts concurrently with bounded parallelism."""

    def __init__(
        self,
        fetcher: Callable = fetch_public_url,
        max_workers: int = 4,
        timeout: float = 5,
    ):
        self.fetcher = fetcher
        self.max_workers = max(1, max_workers)
        self.timeout = timeout

    def fetch(self, servers: list[dict]) -> list[dict]:
        enabled = [
            server
            for server in servers
            if (
                server.get("enabled")
                and server.get("url")
                and server.get("type", "legacy_http") == "legacy_http"
            )
        ]
        if not enabled:
            return []
        workers = min(self.max_workers, len(enabled))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = executor.map(self._fetch_one, enabled)
            return [result for result in results if result is not None]

    def _fetch_one(self, server: dict):
        name = server.get("name", "Unknown")
        url = server["url"]
        try:
            raw_bytes, _ = self.fetcher(url, timeout=self.timeout)
            raw = raw_bytes.decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
                content = (
                    json.dumps(data, indent=2, ensure_ascii=False)
                    if isinstance(data, (dict, list))
                    else str(data)
                )
            except (json.JSONDecodeError, ValueError):
                content = raw
            content = content[:3000]
            if not content.strip():
                return None
            digest = hashlib.sha256(
                f"mcp/{name}/{url}".encode("utf-8")
            ).hexdigest()
            source = ContextSource(
                source_id=f"SRC-{digest[:8].upper()}",
                name=name,
                content=content,
                source_type="mcp",
                confidentiality="internal",
                size_bytes=len(content.encode("utf-8")),
            )
            return {
                "name": name,
                "content": ContextBuilder.build_sources([source]),
            }
        except Exception as exc:
            _logger.warning("MCP fetch failed for %s: %s", name, exc)
            return None
