import json
import urllib.error

import pytest

from pm_os.web.mcp_client import MCPAuthorizationRequired, MCPClient, MCPError
from pm_os.web.safe_http import PublicHTTPResponse


def _response(payload, headers=None, content_type="application/json"):
    return PublicHTTPResponse(
        body=json.dumps(payload).encode(),
        url="https://mcp.example/mcp",
        status=200,
        headers={"content-type": content_type, **(headers or {})},
    )


def test_discovers_server_tools_and_reuses_session():
    calls = []

    def requester(url, **kwargs):
        payload = json.loads(kwargs["body"])
        calls.append((payload, kwargs["headers"]))
        if payload["method"] == "initialize":
            return _response({
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "Example", "version": "2.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            }, {"mcp-session-id": "session-1"})
        if payload["method"] == "tools/list":
            return _response({
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"tools": [{"name": "search", "description": "Search docs"}]},
            })
        return PublicHTTPResponse(b"", url, 202, {})

    discovery = MCPClient(requester=requester).discover({
        "name": "Example",
        "url": "https://mcp.example/mcp",
        "auth": {"type": "bearer", "secret": "token"},
    })

    assert discovery.server_name == "Example"
    assert discovery.tools == [{"name": "search", "description": "Search docs"}]
    assert discovery.resources_supported is True
    assert calls[1][1]["Mcp-Session-Id"] == "session-1"
    assert calls[0][1]["Authorization"] == "Bearer token"


def test_decodes_sse_response():
    def requester(url, **kwargs):
        payload = json.loads(kwargs["body"])
        if payload["method"] == "initialize":
            message = {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "SSE"},
                    "capabilities": {},
                },
            }
            body = f"event: message\ndata: {json.dumps(message)}\n\n".encode()
            return PublicHTTPResponse(body, url, 200, {"content-type": "text/event-stream"})
        return PublicHTTPResponse(b"", url, 202, {})

    assert MCPClient(requester=requester).discover({
        "url": "https://mcp.example/mcp",
        "auth": {"type": "none"},
    }).server_name == "SSE"


def test_reports_authorization_required():
    def requester(url, **kwargs):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    with pytest.raises(MCPAuthorizationRequired):
        MCPClient(requester=requester).discover({
            "url": "https://mcp.example/mcp",
            "auth": {"type": "oauth"},
        })


def test_rejects_non_mcp_response():
    def requester(url, **kwargs):
        return PublicHTTPResponse(b"<html>no</html>", url, 200, {"content-type": "text/html"})

    with pytest.raises(MCPError, match="resposta MCP válida"):
        MCPClient(requester=requester).discover({
            "url": "https://mcp.example/mcp",
            "auth": {"type": "none"},
        })
