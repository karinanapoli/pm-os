import socket
import urllib.error

import pytest

from pm_os.web.safe_http import UnsafeURL, fetch_public_url, validate_public_url


def _resolver_for(*addresses):
    return lambda host, port: [
        (socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
        for address in addresses
    ]


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.31.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
        "192.0.2.1",
    ],
)
def test_validate_public_url_rejects_non_public_destinations(address):
    with pytest.raises(UnsafeURL):
        validate_public_url("https://mcp.example/path", resolver=_resolver_for(address))


def test_validate_public_url_rejects_when_any_dns_answer_is_private():
    with pytest.raises(UnsafeURL):
        validate_public_url(
            "https://mcp.example/path",
            resolver=_resolver_for("93.184.216.34", "127.0.0.1"),
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://service.localhost/admin",
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://169.254.169.254/metadata",
    ],
)
def test_validate_public_url_rejects_local_literals_without_dns(url):
    with pytest.raises(UnsafeURL):
        validate_public_url(url, resolve_dns=False)


def test_validate_public_url_accepts_public_destination_and_removes_fragment():
    result = validate_public_url(
        " HTTPS://mcp.example/path?q=1#secret ",
        resolver=_resolver_for("93.184.216.34"),
    )
    assert result == "https://mcp.example/path?q=1"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:password@mcp.example/path",
        "https://mcp.example:99999/path",
        "https:///missing-host",
    ],
)
def test_validate_public_url_rejects_unsafe_url_shapes(url):
    with pytest.raises(UnsafeURL):
        validate_public_url(url, resolve_dns=False)


def test_fetch_public_url_revalidates_redirect_destination(monkeypatch):
    class RedirectingOpener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                302,
                "Found",
                {"Location": "http://127.0.0.1/admin"},
                None,
            )

    monkeypatch.setattr("pm_os.web.safe_http.urllib.request.build_opener", lambda handler: RedirectingOpener())
    monkeypatch.setattr(
        "pm_os.web.safe_http.socket.getaddrinfo",
        _resolver_for("93.184.216.34"),
    )

    with pytest.raises(UnsafeURL):
        fetch_public_url("https://mcp.example/context")


def test_fetch_public_url_limits_response_size(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, limit):
            return b"x" * limit

    class Opener:
        def open(self, request, timeout):
            return Response()

    monkeypatch.setattr("pm_os.web.safe_http.urllib.request.build_opener", lambda handler: Opener())
    monkeypatch.setattr(
        "pm_os.web.safe_http.socket.getaddrinfo",
        _resolver_for("93.184.216.34"),
    )

    with pytest.raises(UnsafeURL, match="too large"):
        fetch_public_url("https://mcp.example/context", max_bytes=10)
