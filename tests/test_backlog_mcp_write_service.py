import json

import pytest

from pm_os.web.backlog_mcp_write_service import BacklogMCPWriteService
from pm_os.web.mcp_client import MCPError


class FakeClient:
    def __init__(self, fail_title=""):
        self.calls = []
        self.fail_title = fail_title

    def call_tool(self, connection, tool_name, arguments):
        self.calls.append((connection["id"], tool_name, arguments))
        if arguments["item"]["title"] == self.fail_title:
            raise MCPError("external failure")
        return {"external_id": "EXT-" + arguments["item"]["source_id"]}


def package(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "backlog-export-preview.json").write_text(json.dumps({
        "preview_id": "preview-1",
        "status": "confirmed",
        "target": "generic",
        "items": [
            {"source_id": "story-1", "title": "First", "description": "A"},
            {"source_id": "story-2", "title": "Second", "description": "B"},
        ],
    }), encoding="utf-8")


def connection(policy="confirm_writes"):
    return {
        "id": "mcp-1", "name": "Tracker", "type": "mcp", "url": "https://mcp.example.com",
        "enabled": True, "policy": {"mode": policy},
        "capabilities": {"tools": [{"name": "create_issue", "description": "Create"}]},
    }


def test_executes_each_item_and_skips_duplicates_on_retry(tmp_path):
    package(tmp_path)
    client = FakeClient()
    service = BacklogMCPWriteService(client)
    first = service.execute(
        tmp_path, selection="mcp-1::create_issue", connections=[connection()], actor="pm@example.com"
    )
    second = service.execute(
        tmp_path, selection="mcp-1::create_issue", connections=[connection()], actor="pm@example.com"
    )

    assert [item["status"] for item in first["items"]] == ["created", "created"]
    assert [item["status"] for item in second["items"]] == ["duplicate_skipped", "duplicate_skipped"]
    assert len(client.calls) == 2
    assert client.calls[0][2]["idempotency_key"]
    assert len(service.load_receipt(tmp_path)["executions"]) == 2


def test_records_partial_failure_without_replaying_success(tmp_path):
    package(tmp_path)
    client = FakeClient(fail_title="Second")
    service = BacklogMCPWriteService(client)
    result = service.execute(
        tmp_path, selection="mcp-1::create_issue", connections=[connection()], actor="pm@example.com"
    )
    assert [item["status"] for item in result["items"]] == ["created", "failed"]


def test_requires_confirmed_package_and_write_policy(tmp_path):
    service = BacklogMCPWriteService(FakeClient())
    with pytest.raises(MCPError):
        service.execute(tmp_path, selection="mcp-1::create_issue", connections=[connection()], actor="pm")
    package(tmp_path)
    with pytest.raises(MCPError):
        service.execute(
            tmp_path,
            selection="mcp-1::create_issue",
            connections=[connection("read_only")],
            actor="pm",
        )
    assert service.available_tools([connection("read_only")]) == []
