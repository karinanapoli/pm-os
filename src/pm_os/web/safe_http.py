"""Small, SSRF-resistant HTTP client for user-configured integrations."""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 1_000_000
ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeURL(ValueError):
    """Raised when a URL could reach a non-public network destination."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_public_url(
    url: str,
    *,
    resolve_dns: bool = True,
    resolver: Optional[Callable] = None,
) -> str:
    """Return a normalized URL when every resolved address is globally routable."""
    cleaned = url.strip()
    if not cleaned:
        raise UnsafeURL("URL cannot be empty.")

    parsed = urllib.parse.urlsplit(cleaned)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURL("Only HTTP and HTTPS URLs are allowed.")
    if not parsed.hostname:
        raise UnsafeURL("The URL must include a valid hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("Credentials embedded in URLs are not allowed.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL("The URL includes an invalid port.") from exc

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeURL("Private, local, reserved, and link-local destinations are not allowed.")
    try:
        literal_ip = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not literal_ip.is_global:
        raise UnsafeURL("Private, local, reserved, and link-local destinations are not allowed.")

    if resolve_dns:
        resolver = resolver or socket.getaddrinfo
        try:
            addresses = {
                item[4][0].split("%", 1)[0]
                for item in resolver(hostname, port or (443 if parsed.scheme.lower() == "https" else 80))
            }
        except (OSError, UnicodeError) as exc:
            raise UnsafeURL("The server hostname could not be resolved.") from exc
        if not addresses:
            raise UnsafeURL("The server hostname could not be resolved.")
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise UnsafeURL("The server resolved to an invalid IP address.") from exc
            if not ip.is_global:
                raise UnsafeURL("Private, local, reserved, and link-local destinations are not allowed.")

    normalized = parsed._replace(scheme=parsed.scheme.lower(), fragment="").geturl()
    return normalized


def fetch_public_url(
    url: str,
    *,
    timeout: float = 5,
    max_redirects: int = MAX_REDIRECTS,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> tuple[bytes, str]:
    """Fetch a public URL while validating the destination at every redirect."""
    opener = urllib.request.build_opener(_NoRedirect)
    current = url

    for redirect_count in range(max_redirects + 1):
        current = validate_public_url(current, resolve_dns=True)
        request = urllib.request.Request(
            current,
            method="GET",
            headers={"Accept": "text/plain,application/json"},
        )
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise
            location = exc.headers.get("Location")
            if not location:
                raise UnsafeURL("The server returned a redirect without a destination.") from exc
            if redirect_count == max_redirects:
                raise UnsafeURL("The server exceeded the redirect limit.") from exc
            current = urllib.parse.urljoin(current, location)
            continue

        with response:
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise UnsafeURL("The server response is too large.")
            return body, current

    raise UnsafeURL("The server exceeded the redirect limit.")
