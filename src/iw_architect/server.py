"""MCP server entry point for the Infinite Worlds Architect plugin.

Run with:  python -m iw_architect.server
Or:        uv run python -m iw_architect.server

Tools registered alphabetically per the design brief.
"""

from mcp.server.fastmcp import FastMCP

from iw_architect.tools.analysis import audit_world, compare_worlds, get_diff_summary
from iw_architect.tools.helpers import (
    confirm_path,
    create_new_world_json,
    make_draft_world,
    mint_ids,
)
from iw_architect.tools.inspection import (
    format_world_for_review,
    get_schema_summary,
    read_world_field,
)
from iw_architect.validator import validate_world

mcp = FastMCP("iw-json-tools")

# Register tools in alphabetical order
mcp.tool()(audit_world)
mcp.tool()(compare_worlds)
mcp.tool()(confirm_path)
mcp.tool()(format_world_for_review)
mcp.tool()(get_diff_summary)
mcp.tool()(get_schema_summary)
mcp.tool()(make_draft_world)
mcp.tool()(mint_ids)
mcp.tool()(read_world_field)
mcp.tool()(create_new_world_json)
mcp.tool()(validate_world)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
