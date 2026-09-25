import importlib


def test_server_registers_cursor_tools(monkeypatch, tmp_path):
    monkeypatch.setenv("PM_OS_WORKSPACE_DIR", str(tmp_path))
    import pm_os.mcp_server as server_module
    module = importlib.reload(server_module)

    names = {tool.name for tool in module.mcp._tool_manager.list_tools()}

    assert names == {
        "list_initiatives",
        "get_initiative_context",
        "get_initiative_specification",
        "get_initiative_prd",
        "add_technical_discovery",
        "propose_changes",
        "get_proposal_status",
    }


def test_server_delegates_proposals_without_applying_them(monkeypatch, tmp_path):
    monkeypatch.setenv("PM_OS_WORKSPACE_DIR", str(tmp_path))
    import pm_os.mcp_server as server_module
    module = importlib.reload(server_module)

    class FakeService:
        def propose_changes(self, initiative_name, *, proposals, specification_version):
            return {
                "initiative": initiative_name,
                "count": len(proposals),
                "version": specification_version,
                "status": "pending_review",
            }

    module.service = FakeService()
    result = module.propose_changes(
        "INT-001",
        [{"field": "requirements"}],
        4,
    )

    assert result == {
        "initiative": "INT-001",
        "count": 1,
        "version": 4,
        "status": "pending_review",
    }
