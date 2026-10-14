"""Detect a local Ollama server so Demo users can switch to a real provider in one click."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_CACHE_SECONDS = 30.0
_cache: dict[str, tuple[float, list[str]]] = {}
_lock = threading.Lock()


def detect_ollama_models(base_url: str, timeout: float = 0.4) -> list[str]:
    """Return installed model names when a *local* Ollama answers, else an empty list.

    Only loopback URLs are probed, the result is cached briefly, and any failure
    is treated as "not available" so page rendering never depends on Ollama.
    """
    parsed = urllib.parse.urlparse(base_url or "")
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _LOCAL_HOSTS:
        return []
    now = time.monotonic()
    with _lock:
        cached = _cache.get(base_url)
        if cached and now - cached[0] < _CACHE_SECONDS:
            return list(cached[1])
    models: list[str] = []
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=timeout) as response:  # noqa: S310 - loopback only
            payload = json.loads(response.read(256_000).decode("utf-8"))
        models = [
            str(item.get("name"))
            for item in payload.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]
    except (OSError, ValueError, urllib.error.URLError):
        models = []
    with _lock:
        _cache[base_url] = (now, models)
    return list(models)


def clear_cache() -> None:
    with _lock:
        _cache.clear()
