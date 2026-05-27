# Infinite Worlds Architect

A Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds through conversation. The plugin exposes MCP tools that validate, scaffold, and analyze world JSON files, plus skills that guide field-by-field world creation and editing workflows.

## What this is

Infinite Worlds is a third-party storytelling platform where authors design **worlds** — collections of characters, NPCs, instructions, tracked state, and conditional triggers that the platform uses to run interactive stories. A world is persisted as a single JSON file conforming to the v2.1 schema documented in [`WORLD_JSON_SCHEMA_v2.1.md`](./WORLD_JSON_SCHEMA_v2.1.md).

This plugin assists an author who is building or editing such a world by talking to Claude in a Claude Code session. The plugin:

- Validates world JSON against the platform's schema before sending it live
- Scaffolds new worlds from sane defaults
- Audits quality (token budgets, trigger cycles, redundancy detection)
- Provides one model-invoked skill (`world-architect`) and three guided slash commands (`/new-world`, `/modify-world`, `/spinoff-world`)

The plugin has **no write tools** — Claude edits world JSON directly using its built-in `Read`/`Edit`/`Write`. The plugin is the validator, analyst, and helper; the agent is the author.

## Install

**Prerequisite:** [`uv`](https://docs.astral.sh/uv/) must be on your PATH — the MCP server is launched with `uv run` at session start and will fail to start without it. If tools are missing after install, check `/mcp` to confirm the `iw-json-tools` server is connected.

Installing the plugin is a **two-step process** in Claude Code: first add this repository as a *marketplace*, then install the plugin from that marketplace.

1. **Add the marketplace** (run inside any Claude Code session):

   ```
   /plugin marketplace add moose-cove/infinite-worlds-architect
   ```

   This registers the marketplace defined in [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json) under the name `iw-architect-marketplace`.

2. **Install the plugin from the marketplace:**

   ```
   /plugin install infinite-worlds-architect@iw-architect-marketplace
   ```

3. **Reload Claude Code** when prompted. The MCP server (`iw-json-tools`) starts automatically — no separate launch needed.

To update later, run both:

```
/plugin marketplace update iw-architect-marketplace
/plugin install infinite-worlds-architect@iw-architect-marketplace
```

To remove: `/plugin uninstall infinite-worlds-architect@iw-architect-marketplace`.

## Using the plugin

Once installed, the plugin contributes three things to your Claude Code session:

### 1. The `world-architect` skill (auto-activated)

This is a **model-invoked skill** — you do not run it as a slash command. Claude loads it automatically when you say something like:

- *"Help me build an Infinite Worlds world."*
- *"I want to design a world for Infinite Worlds."*
- *"What can the Infinite Worlds plugin do?"*
- *"How do I use the world tools?"*

Once activated, Claude has on-demand access to the schema reference, per-field authoring guidance (`INTRODUCING_THE_STORY.md`, `MAIN_INSTRUCTIONS.md`, `TRACKED_ITEMS.md`, `TRIGGER_EVENTS.md`, etc.), and the MCP tool surface listed below. Use this skill for **ad-hoc questions and free-form world editing** that don't fit the structured command workflows.

### 2. Slash commands (structured workflows)

| Command | Purpose | Argument |
|---|---|---|
| `/infinite-worlds-architect:new-world <output_path>` | Guided field-by-field creation of a brand-new world from scratch. | Path where the new `world.json` should be written. |
| `/infinite-worlds-architect:modify-world <world_path>` | Guided field-by-field editing of an existing world, with per-change approval. | Path to the existing `world.json`. |
| `/infinite-worlds-architect:spinoff-world <source_path> <target_path>` | Derive a divergent variant from an existing world, keeping the original intact. | Source path, then target path. |

Each command walks you through the relevant fields, validates after each change, and respects the source-of-truth rules in [`CLAUDE.md`](./CLAUDE.md): read before write and pass-through preservation (which keeps `schemaVersion` and any unknown fields intact across edits).

### 3. MCP tools (callable by Claude)

The skill and commands have access to these tools — you generally won't call them directly, but knowing they exist helps when asking Claude for specific operations:

| Tool | What it does |
|---|---|
| `validate_world(world_path)` | Strict schema check — reports every error that would cause the platform to reject the world. |
| `audit_world(world_path)` | Quality analysis — token budgets, trigger cycles, redundancy detection. |
| `scaffold_world(output_path, title, nsfw)` | Create a fresh, valid world JSON at the given path. |
| `read_world_field(world_path, path)` | Read a single field using dot/bracket path syntax. |
| `format_world_for_review(world_path)` | Render the world as human-readable Markdown for review. |
| `get_schema_summary()` | Structured metadata about entity types, fields, and enum values. |
| `mint_ids(kind, count)` | Generate platform-format IDs for new entities. |
| `confirm_path(path)` | Resolve and verify a file path before acting on it. |
| `compare_worlds(world_path_a, world_path_b)` | Structural diff between two worlds. |
| `get_diff_summary(original_path, current_path)` | Human-readable narrative of what changed. |

### Typical session

```text
You:    /infinite-worlds-architect:new-world ./my-world.json
Claude: <walks you through title, description, background, firstInput…>
        <calls scaffold_world, then validate_world after each edit>

You:    Add a player-only number tracked item called "reputation",
        with update instructions to keep it between 0 and 100.
Claude: <invokes world-architect skill knowledge, edits world.json,
         calls validate_world to confirm>

You:    /infinite-worlds-architect:spinoff-world ./my-world.json ./my-world-nsfw.json
Claude: <copies, then guides edits for the variant>
```

Open any `world.json` and ask Claude what's wrong, what could be tighter, or what to add next — the skill will pull the right reference file on demand.

## Development setup

Requires Python 3.12.13 (pinned via [`.tool-versions`](./.tool-versions) for asdf users) and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras       # creates .venv/ and installs runtime + dev deps
uv run pre-commit install
uv run pytest
```

If you'd rather use stdlib `venv` + `pip`, see the legacy block in [`CLAUDE.md`](./CLAUDE.md#setup).

The MCP server can also be started manually for debugging:

```bash
uv run python -m iw_architect.server
```

## Where to read more

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Project conventions, file structure, pre-commit policy, and the workflow for adding a new platform feature. Loaded automatically into every Claude Code session in this repo. |
| [`DESIGN_BRIEF_v2.md`](./DESIGN_BRIEF_v2.md) | The full design spec the implementation was built against. Architecture rationale, tool surface, validator check list, testing strategy. |
| [`WORLD_JSON_SCHEMA_v2.1.md`](./WORLD_JSON_SCHEMA_v2.1.md) | Human-readable explanation of every field in the world JSON schema. The canonical JSON Schema artifact lives next to it at `skills/world-architect/references/world_v2.1.schema.json`. |
| [`example-world-schema-v2.1.json`](./example-world-schema-v2.1.json) | The canonical fixture. Per design brief §3, this file is the ultimate source of truth — if `validate_world` rejects it, the validator is wrong. |

## License

MIT. See `.claude-plugin/plugin.json` for the full manifest.
