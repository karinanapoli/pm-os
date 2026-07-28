import pytest

from pm_os.web.mcp_connections import (
    build_connection,
    businessmap_endpoint,
    normalize_connection,
    public_connection,
)


def test_businessmap_endpoint_is_derived_from_safe_subdomain():
    assert businessmap_endpoint("Acme-1") == "https://acme-1.businessmap.io/baiApi/v1/mcp"
    with pytest.raises(ValueError):
        businessmap_endpoint("https://evil.example/path")


def test_old_entry_is_preserved_as_legacy_http_source():
    old = {"name": "Docs", "url": "https://docs.example/context", "enabled": True}
    upgraded = normalize_connection(old)
    assert upgraded["type"] == "legacy_http"
    assert upgraded["transport"] == "http_get"
    assert upgraded["status"]["state"] == "not_tested"
    assert old == {"name": "Docs", "url": "https://docs.example/context", "enabled": True}


def test_public_connection_never_exposes_secret():
    connection = build_connection(
        name="Private",
        url="https://mcp.example/mcp",
        auth_type="bearer",
        auth_secret="top-secret",
    )
    public = public_connection(connection)
    assert public["auth"]["secret"] == ""
    assert public["auth"]["has_secret"] is True


def test_rejects_header_injection():
    with pytest.raises(ValueError, match="header"):
        build_connection(
            name="Unsafe",
            url="https://mcp.example/mcp",
            auth_type="api_key",
            auth_secret="secret",
            auth_header="X-Key\r\nInjected: yes",
        )


def test_oauth_connection_is_explicitly_pending_authorization():
    connection = build_connection(
        name="Businessmap",
        url="https://acme.businessmap.io/baiApi/v1/mcp",
        preset="businessmap",
        auth_type="oauth",
    )
    assert connection["status"]["state"] == "authorization_required"
