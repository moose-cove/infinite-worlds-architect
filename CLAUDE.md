# Infinite Worlds Architect

Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds.

## Project structure

```
src/iw_architect/
├── server.py          # MCP server entry point (FastMCP, stdio transport)
├── validator.py       # Two-tier world validator (jsonschema + custom checks)
├── schema_model.py    # Structured schema metadata for get_schema_summary()
├── world_schema.json  # JSON Schema v2.1 artifact (Tier 1 validator)
└── tools/
    ├── inspection.py  # read_world_field, format_world_for_review, get_schema_summary
    ├── helpers.py     # scaffold_world, mint_ids, confirm_path
    └── analysis.py    # audit_world, compare_worlds, get_diff_summary

tests/
├── test_round_trip.py  # Fixture round-trip + scaffold tests (most critical)
└── test_validator.py   # Negative tests for every error class in §4.6

skills/
├── world-architect/    # Top-level discovery skill
│   └── references/WORLD_JSON_SCHEMA_v2.1.md
├── new-world/          # Guided world creation workflow
├── modify-world/       # Edit existing world workflow
└── spinoff-world/      # Variant world workflow

.claude-plugin/plugin.json   # Plugin manifest
.mcp.json                    # MCP server spawn configuration
```

## Setup

```bash
uv sync --all-extras
uv run pytest
```

## Running the MCP server

```bash
uv run python -m iw_architect.server
```

## Source-of-truth rules (from DESIGN_BRIEF_v2.md §3)

1. **`example-world-schema-v2.1.json` is the schema.** If `validate_world` reports errors on the fixture, the validator is wrong — fix the validator to accept the fixture.
2. **Read before writing.** Always call `Read` on the JSON before any `Edit`.
3. **Pass-through preservation.** Unknown fields survive because the agent edits in place.
4. **`schemaVersion` is load-bearing.** Read and write it on every world.
5. **The validator enforces; the schema doc explains; the fixture is ground truth.**

## Design constraints

- **No write tools.** The plugin has no add/modify/remove MCP tools. The agent edits `world.json` directly with Claude Code's native `Read`, `Edit`, `Write` tools.
- **Single validator.** All schema knowledge lives in `validator.py` + `world_schema.json`. Update only those files when the platform schema evolves.
- **Warn, don't error** on unknown top-level keys, unknown effect types, and future schema versions — the platform may add fields the validator doesn't know about.

## Adding a new platform feature

1. Add the new field/effect/condition type to `world_schema.json`
2. Add its shape to `schema_model.py` (SCHEMA_SUMMARY)
3. Add cross-reference checks to `validator.py` if needed
4. Add a negative test in `tests/test_validator.py`
5. Verify the fixture still passes with `uv run pytest`

## Open questions (from DESIGN_BRIEF_v2.md §9)

- `illustrationStyle*HighPriority` / `LowPriority` coexistence rules with older `imageStyle*` fields
- `recommendedAIModel` full enum of valid values (fixture only shows `null`)

These are preserved verbatim and not validated beyond type-checking until a fixture clarifies them.

## Python version

3.12.13 (pinned in `.tool-versions`)

## Tools and libraries

| Tool | Purpose |
|---|---|
| `uv` | Package and environment management |
| `mcp` | Official Python MCP SDK (FastMCP, stdio transport) |
| `jsonschema` | Tier 1 structural validation |
| `ruff` | Linting and formatting |
| `pytest` + `pytest-cov` | Testing (80% coverage threshold) |
| `pre-commit` | Pre-commit hooks (lint + tests) |
