import threading

from pm_os.web.mcp_context_service import MCPContextService


def test_fetches_enabled_servers_and_preserves_configuration_order():
    barrier = threading.Barrier(2)

    def fetcher(url, timeout):
        barrier.wait(timeout=1)
        return f'{{"url": "{url}"}}'.encode(), url

    service = MCPContextService(fetcher=fetcher, max_workers=2)
    results = service.fetch([
        {"name": "First", "url": "https://first.example", "enabled": True},
        {"name": "Disabled", "url": "https://off.example", "enabled": False},
        {"name": "Second", "url": "https://second.example", "enabled": True},
    ])

    assert [result["name"] for result in results] == ["First", "Second"]
    assert "SRC-" in results[0]["content"]
    assert "first.example" in results[0]["content"]


def test_failure_or_empty_response_does_not_block_other_servers():
    def fetcher(url, timeout):
        if "broken" in url:
            raise OSError("unavailable")
        if "empty" in url:
            return b"   ", url
        return b"plain context", url

    results = MCPContextService(fetcher=fetcher).fetch([
        {"name": "Broken", "url": "https://broken.example", "enabled": True},
        {"name": "Empty", "url": "https://empty.example", "enabled": True},
        {"name": "Healthy", "url": "https://healthy.example", "enabled": True},
    ])

    assert [result["name"] for result in results] == ["Healthy"]
    assert "plain context" in results[0]["content"]


def test_returns_immediately_when_no_server_is_enabled():
    called = False

    def fetcher(url, timeout):
        nonlocal called
        called = True

    results = MCPContextService(fetcher=fetcher).fetch([
        {"name": "Off", "url": "https://off.example", "enabled": False}
    ])

    assert results == []
    assert called is False
