import sys

from pm_os.web.mcp_stdio_client import MCPStdioClient


def test_discovers_tools_from_local_stdio_process(tmp_path):
    server = tmp_path / "server.py"
    server.write_text(
        """
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "Local Test", "version": "1.0"},
            "capabilities": {"tools": {}, "resources": {}},
        }
    elif message.get("method") == "tools/list":
        result = {
            "tools": [{"name": "search", "description": "Search local files"}],
        }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
""",
        encoding="utf-8",
    )

    discovery = MCPStdioClient(timeout=3).discover({
        "name": "Local",
        "command": sys.executable,
        "args": [str(server)],
        "env": {},
    })

    assert discovery.server_name == "Local Test"
    assert discovery.tools == [{
        "name": "search",
        "description": "Search local files",
    }]
    assert discovery.resources_supported is True
