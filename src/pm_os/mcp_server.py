"""Installable PM Studio MCP server for local agents such as Cursor."""

from mcp.server.fastmcp import FastMCP

from pm_os.web.cursor_mcp_service import CursorMCPService


mcp = FastMCP("PM Studio")
service = CursorMCPService()


@mcp.tool()
def list_initiatives() -> list[str]:
    """List initiatives explicitly made available to external agents."""
    return [item["id"] for item in service.list_initiatives()]


@mcp.tool()
def get_initiative_context(initiative_name: str) -> str:
    """Return the consolidated source context for one shared initiative."""
    return service.get_initiative_context(initiative_name)["context"]


@mcp.tool()
def get_initiative_specification(initiative_name: str) -> dict:
    """Return the structured, versioned specification for a shared initiative."""
    return service.get_specification(initiative_name)


@mcp.tool()
def get_initiative_prd(initiative_name: str) -> str:
    """Return the latest PRD for one shared initiative."""
    return service.get_prd(initiative_name)


@mcp.tool()
def add_technical_discovery(
    initiative_name: str,
    summary: str,
    reason: str,
    specification_version: int,
    references: list[str] | None = None,
) -> dict:
    """Submit a code-backed discovery for human review in PM Studio."""
    return service.add_technical_discovery(
        initiative_name,
        summary=summary,
        reason=reason,
        specification_version=specification_version,
        references=references,
    )


@mcp.tool()
def propose_changes(
    initiative_name: str,
    proposals: list[dict],
    specification_version: int,
) -> dict:
    """Submit structured product changes without applying them automatically."""
    return service.propose_changes(
        initiative_name,
        proposals=proposals,
        specification_version=specification_version,
    )


@mcp.tool()
def get_proposal_status(initiative_name: str, proposal_ids: list[str]) -> list[dict]:
    """Return the human-review status of proposals previously submitted by an agent."""
    return service.get_proposal_status(initiative_name, proposal_ids)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

