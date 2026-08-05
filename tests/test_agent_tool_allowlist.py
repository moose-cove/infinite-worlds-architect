"""Agent frontmatter `tools:` allowlist coverage.

An agent's frontmatter ``tools:`` list is a **whitelist**: anything omitted is denied. So a
tool the agent's own body instructs it to call, but which is missing from the list, is
silently uncallable — the agent reads an imperative it cannot obey, and the failure surfaces
only at runtime as a refused tool call.

This shipped once already. ``agents/world-architect.md`` made ``make_draft_world`` the
mandatory first action of every modify flow ("never edit the file the author handed you" —
the agent's central safety property), while the tool was absent from the allowlist. The same
gap covered the three story-export tools that ``commands/sequel-world.md`` drives.

Nothing in the diff of either file reveals the mismatch; you have to cross-reference the
frontmatter against the body against the MCP server's registrations. That is what this does.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SERVER_PY = REPO_ROOT / "src" / "iw_architect" / "server.py"

# Agents that may call this plugin's MCP tools, and the tool-name prefix they must use.
_AGENT_FILES = ("agents/world-architect.md",)
_TOOL_PREFIX = "mcp__plugin_infinite-worlds-architect_iw-json-tools__"

_REGISTERED_RE = re.compile(r"^mcp\.tool\(\)\((\w+)\)", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _registered_tools() -> set[str]:
    """Every tool name registered on the FastMCP server."""
    return set(_REGISTERED_RE.findall(SERVER_PY.read_text()))


def _frontmatter_and_body(path: Path) -> tuple[str, str]:
    text = path.read_text()
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        pytest.fail(f"{path.relative_to(REPO_ROOT)} has no parseable `---` frontmatter block")
    return match.group(1), text[match.end() :]


def _allowlisted_tools(frontmatter: str) -> set[str]:
    """Bare tool names from the frontmatter `tools:` list (prefix stripped)."""
    return {
        line.strip().removeprefix("- ").strip().removeprefix(_TOOL_PREFIX)
        for line in frontmatter.splitlines()
        if _TOOL_PREFIX in line
    }


def test_server_registers_tools():
    """Guard the regex itself — a silent zero-match would make every test below vacuous."""
    assert len(_registered_tools()) >= 10, _registered_tools()


@pytest.mark.parametrize("rel_path", _AGENT_FILES)
def test_agent_allowlists_every_tool_its_body_names(rel_path):
    """Every registered MCP tool named in an agent's body must be in its `tools:` allowlist."""
    path = REPO_ROOT / rel_path
    frontmatter, body = _frontmatter_and_body(path)
    allowlisted = _allowlisted_tools(frontmatter)

    missing = sorted(
        tool
        for tool in _registered_tools()
        # `\b` alone would let `make_draft_world` match inside a longer identifier; the body
        # refers to tools as bare names in prose and as `tool(...)` calls in fenced blocks.
        if re.search(rf"(?<![\w.]){re.escape(tool)}(?![\w])", body) and tool not in allowlisted
    )

    assert not missing, (
        f"{rel_path} instructs the agent to use tool(s) missing from its frontmatter "
        f"`tools:` allowlist, so the calls will be denied at runtime: {missing}. "
        f"Add them as {_TOOL_PREFIX}<name>."
    )


@pytest.mark.parametrize("rel_path", _AGENT_FILES)
def test_agent_allowlist_has_no_unregistered_tools(rel_path):
    """The reverse drift: an allowlisted tool that no longer exists on the server."""
    frontmatter, _ = _frontmatter_and_body(REPO_ROOT / rel_path)
    unknown = sorted(_allowlisted_tools(frontmatter) - _registered_tools())
    assert not unknown, (
        f"{rel_path} allowlists MCP tool(s) that {SERVER_PY.name} does not register "
        f"(renamed or removed?): {unknown}"
    )
