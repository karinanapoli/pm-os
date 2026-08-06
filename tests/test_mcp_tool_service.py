import pytest

from pm_os.web.mcp_client import MCPError
from pm_os.web.mcp_tool_service import MCPToolService


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    def call_tool(self, connection, tool_name, arguments):
        self.calls.append((connection, tool_name, arguments))
        return {"content": [{"type": "text", "text": "3 riscos"}]}


def _connection(policy="read_only"):
    return {
        "id": "mcp-example",
        "name": "Roadmap",
        "url": "https://mcp.example/mcp",
        "type": "mcp",
        "enabled": True,
        "policy": {"mode": policy},
        "capabilities": {
            "tools": [{"name": "search", "description": "Search roadmap"}],
        },
    }


def test_lists_and_executes_only_explicit_read_only_tool():
    client = FakeMCPClient()
    service = MCPToolService(client=client)

    assert service.available_tools([_connection()]) == [{
        "value": "mcp-example::search",
        "connection": "Roadmap",
        "name": "search",
        "description": "Search roadmap",
    }]
    result = service.execute([_connection()], "mcp-example::search", '{"query":"riscos"}')

    assert client.calls[0][1:] == ("search", {"query": "riscos"})
    assert result.connection_name == "Roadmap"
    assert "3 riscos" in result.content


def test_blocks_write_policy_forged_tool_and_invalid_arguments():
    service = MCPToolService(client=FakeMCPClient())

    assert service.available_tools([_connection("confirm_writes")]) == []
    with pytest.raises(MCPError, match="não está disponível"):
        service.execute([_connection("confirm_writes")], "mcp-example::search", "{}")
    with pytest.raises(MCPError, match="não foi autorizada"):
        service.execute([_connection()], "mcp-example::delete", "{}")
    with pytest.raises(MCPError, match="JSON válido"):
        service.execute([_connection()], "mcp-example::search", "not-json")
