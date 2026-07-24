"""Trusted host and externally visible URL configuration."""

from urllib.parse import urlsplit

_DEFAULT_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "testserver")


def allowed_hosts_from_env(value: str) -> list[str]:
    hosts = [host.strip().lower() for host in value.split(",") if host.strip()]
    return hosts or list(_DEFAULT_ALLOWED_HOSTS)


def external_base_url(
    request_base_url: str,
    configured_url: str = "",
    production: bool = False,
) -> str:
    candidate = (configured_url or request_base_url).strip().rstrip("/")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Public URL must be an absolute HTTP(S) URL.")
    if production and parsed.scheme != "https":
        raise ValueError("Public URL must use HTTPS in production.")
    return candidate
