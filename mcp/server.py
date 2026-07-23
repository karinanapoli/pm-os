"""PM Studio MCP server.

Run with: python mcp/server.py
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from pm_os.context_builder import ContextBuilder
from pm_os.repositories.initiative_repository import InitiativeRepository


mcp = FastMCP("PM Studio")
repository = InitiativeRepository()
context_builder = ContextBuilder()


@mcp.tool()
def list_initiatives() -> list[str]:
    """List the initiatives available in the current PM Studio workspace."""
    return repository.list_names()


@mcp.tool()
def get_initiative_context(initiative_name: str) -> str:
    """Return the consolidated context for one initiative."""
    for initiative in repository.list_initiatives():
        if initiative.name == initiative_name:
            return context_builder.build(initiative)
    raise ValueError(f"Initiative '{initiative_name}' not found.")


@mcp.tool()
def get_initiative_prd(initiative_name: str) -> str:
    """Return the latest PRD for one initiative."""
    if initiative_name not in repository.list_names():
        raise ValueError(f"Initiative '{initiative_name}' not found.")
    initiative_dir = (repository.initiatives_path / initiative_name).resolve()
    prd_path = initiative_dir / "artifacts" / "prd.md"
    if not prd_path.is_file() or initiative_dir not in prd_path.resolve().parents:
        raise ValueError(f"PRD for initiative '{initiative_name}' not found.")
    return prd_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()
