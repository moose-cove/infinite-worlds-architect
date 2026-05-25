# Infinite Worlds Architect

A Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds through conversation. The plugin exposes MCP tools that validate, scaffold, and analyze world JSON files, plus skills that guide field-by-field world creation and editing workflows.

## What this is

Infinite Worlds is a third-party storytelling platform where authors design **worlds** — collections of characters, NPCs, instructions, tracked state, and conditional triggers that the platform uses to run interactive stories. A world is persisted as a single JSON file conforming to the v2.1 schema documented in [`WORLD_JSON_SCHEMA_v2.1.md`](./WORLD_JSON_SCHEMA_v2.1.md).

This plugin assists an author who is building or editing such a world by talking to Claude in a Claude Code session. The plugin:

- Validates world JSON against the platform's schema before sending it live
- Scaffolds new worlds from sane defaults
- Audits quality (token budgets, trigger cycles, redundancy detection)
- Provides four guided workflow skills (`world-architect`, `new-world`, `modify-world`, `spinoff-world`)

The plugin has **no write tools** — Claude edits world JSON directly using its built-in `Read`/`Edit`/`Write`. The plugin is the validator, analyst, and helper; the agent is the author.

## Quick install

Requires Python 3.12.13 (pinned via [`.tool-versions`](./.tool-versions) for asdf users).

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pre-commit install
.venv/bin/pytest
```

The MCP server is spawned by Claude Code via [`.mcp.json`](./.mcp.json) when the plugin is loaded — no separate launch needed.

## Where to read more

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Project conventions, file structure, pre-commit policy, and the workflow for adding a new platform feature. Loaded automatically into every Claude Code session in this repo. |
| [`DESIGN_BRIEF_v2.md`](./DESIGN_BRIEF_v2.md) | The full design spec the implementation was built against. Architecture rationale, tool surface, validator check list, testing strategy. |
| [`WORLD_JSON_SCHEMA_v2.1.md`](./WORLD_JSON_SCHEMA_v2.1.md) | Human-readable explanation of every field in the world JSON schema. The canonical JSON Schema artifact lives next to it at `skills/world-architect/references/world_v2.1.schema.json`. |
| [`example-world-schema-v2.1.json`](./example-world-schema-v2.1.json) | The canonical fixture. Per design brief §3, this file is the ultimate source of truth — if `validate_world` rejects it, the validator is wrong. |

## License

MIT. See `.claude-plugin/plugin.json` for the full manifest.
