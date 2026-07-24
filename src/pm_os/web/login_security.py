"""Login throttling and trusted proxy address handling."""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional


def resolve_client_ip(
    remote_address: str,
    forwarded_for: str = "",
    trusted_proxy_count: int = 0,
) -> str:
    """Return a validated client address without trusting proxy headers by default."""
    remote = _valid_ip(remote_address) or "unknown"
    if trusted_proxy_count <= 0 or not forwarded_for:
        return remote

    forwarded = [
        _valid_ip(raw_address.strip())
        for raw_address in forwarded_for.split(",")
    ]
    if any(address is None for address in forwarded):
        return remote
    if len(forwarded) < trusted_proxy_count:
        return remote
    return forwarded[-trusted_proxy_count]


def _valid_ip(value: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


class LoginRateLimiter:
    """Bound failed login attempts per client within a rolling time window."""

    def __init__(
        self,
        max_attempts: int = 10,
        window_seconds: int = 300,
        max_clients: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self.clock = clock
        self._failures: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()

    def is_blocked(self, client_key: str) -> bool:
        with self._lock:
            attempts = self._recent_attempts(client_key, self.clock())
            return len(attempts) >= self.max_attempts

    def record_failure(self, client_key: str) -> None:
        with self._lock:
            now = self.clock()
            attempts = self._recent_attempts(client_key, now)
            attempts.append(now)
            self._failures[client_key] = attempts
            self._failures.move_to_end(client_key)
            while len(self._failures) > self.max_clients:
                self._failures.popitem(last=False)

    def reset(self, client_key: str) -> None:
        with self._lock:
            self._failures.pop(client_key, None)

    def _recent_attempts(self, client_key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        attempts = [
            attempt
            for attempt in self._failures.get(client_key, [])
            if attempt > cutoff
        ]
        if attempts:
            self._failures[client_key] = attempts
            self._failures.move_to_end(client_key)
        else:
            self._failures.pop(client_key, None)
        return attempts
