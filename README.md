# Infinite Worlds Architect

A Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds through conversation. The plugin exposes MCP tools that validate, scaffold, and analyze world JSON files, a `world-architect` agent that authors and debugs worlds end-to-end, and slash commands that walk authors through structured field-by-field workflows.

## What this is

Infinite Worlds is a third-party storytelling platform where authors design **worlds** — collections of characters, NPCs, instructions, tracked state, and conditional triggers that the platform uses to run interactive stories. A world is persisted as a single JSON file conforming to the v2.4 schema documented in [`references/WORLD_JSON_SCHEMA_v2.4.md`](./references/WORLD_JSON_SCHEMA_v2.4.md).

This plugin assists an author who is building or editing such a world by talking to Claude in a Claude Code session. The plugin:

- Validates world JSON against the platform's schema before sending it live
- Scaffolds new worlds from sane defaults
- Audits quality (token budgets, trigger cycles, redundancy detection)
- Provides one `world-architect` agent and four guided slash commands (`/new-world`, `/modify-world`, `/spinoff-world`, `/sequel-world`)

The plugin has **no write tools** — Claude edits world JSON directly using its built-in `Read`/`Edit`/`Write`. The plugin is the validator, analyst, and helper; the agent is the author.

## Install

**Prerequisite:** [`uv`](https://docs.astral.sh/uv/) must be on your PATH — the MCP server is launched with `uv run` at session start and will fail to start without it.

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

### 1. The `world-architect` agent

This is an **autonomous subagent** that handles world authoring and debugging end-to-end. It knows the v2.4 schema deeply, can author new worlds, edit existing ones, debug trigger/tracked-item issues, and answer Infinite Worlds platform questions grounded in the schema → fixture → reference docs hierarchy. It will follow the edit-flow contract (read, plan, mint IDs, show diffs, edit, validate, audit) without being prompted for each step.

The agent is reached two ways:

- **Automatically as a subagent** when you describe authoring or debugging work in natural language — e.g. *"I want to build a noir detective world..."*, *"My trigger doesn't fire even though..."*, *"Add a wandering merchant NPC to my world..."*. Claude routes the task to the agent.
- **Inline through a slash command** (`/new-world`, `/modify-world`, `/spinoff-world`, `/sequel-world`). Each command `@`-references the agent file, so the main session adopts the agent's persona before walking you through that command's specific workflow — preserving the field-by-field approval loop that needs multi-turn user interaction.

On-demand reference material lives at [`references/`](./references/) at the plugin root — the agent loads individual files as needed.

### 2. Slash commands (structured workflows)

| Command | Purpose | Argument |
|---|---|---|
| `/infinite-worlds-architect:new-world <output_path>` | Guided field-by-field creation of a brand-new world from scratch. | Path where the new `world.json` should be written. |
| `/infinite-worlds-architect:modify-world <world_path>` | Guided field-by-field editing of an existing world, with per-change approval. | Path to the existing `world.json`. |
| `/infinite-worlds-architect:spinoff-world <source_path> <target_path>` | Derive a divergent variant from an existing world, keeping the original intact. | Source path, then target path. |
| `/infinite-worlds-architect:sequel-world <source_path> <story_export_path...> <target_path>` | Build a sequel that begins where a played story left off, evolving fields from what actually happened (each proposal cites its evidence). | Source world path, one or more story-export `.txt` paths, then target path. |

Each command walks you through the relevant fields, validates after each change, and respects the source-of-truth rules in [`CLAUDE.md`](./CLAUDE.md): read before write and pass-through preservation (which keeps `schemaVersion` and any unknown fields intact across edits).

### 3. MCP tools (callable by Claude)

The agent and commands have access to these tools — you generally won't call them directly, but knowing they exist helps when asking Claude for specific operations:

| Tool | What it does |
|---|---|
| `validate_world(world_path)` | Strict schema check — reports every error that would cause the platform to reject the world. |
| `audit_world(world_path)` | Quality analysis — token budgets, trigger cycles, redundancy detection. |
| `create_new_world_json(output_path, title, nsfw)` | Create a fresh, valid world JSON at the given path. |
| `read_world_field(world_path, path)` | Read a single field using dot/bracket path syntax. |
| `format_world_for_review(world_path)` | Render the world as human-readable Markdown and write it to `<world_stem>.review.md` next to the input. Returns `{"success": "<path>"}` or `{"error": "<details>"}`. |
| `get_schema_summary()` | Structured metadata about entity types, fields, and enum values. |
| `mint_ids(kind, count)` | Generate platform-format IDs for new entities. |
| `confirm_path(path)` | Resolve and verify a file path before acting on it. |
| `compare_worlds(world_path_a, world_path_b)` | Structural diff between two worlds. |
| `get_diff_summary(original_path, current_path)` | Human-readable narrative of what changed. |

### Typical session

```text
You:    /infinite-worlds-architect:new-world ./my-world.json
Claude: <walks you through title, description, background, firstInput…>
        <calls create_new_world_json, then validate_world after each edit>

You:    Add a number tracked item visible only to the AI called "reputation",
        with update instructions to keep it between 0 and 100 and modify it based on how other characters in town perceive the player.
Claude: <invokes the world-architect agent, edits world.json,
         calls validate_world to confirm>

You:    /infinite-worlds-architect:spinoff-world ./my-world.json ./my-world-nsfw.json
Claude: <copies, then guides edits for the variant>

You:    /infinite-worlds-architect:sequel-world ./my-world.json ./session-1-20.txt ./my-world-2.json
Claude: <extracts the played story, then proposes each evolved field with cited evidence>
```

Open any `world.json` and ask Claude what's wrong, what could be tighter, or what to add next — the agent will pull the right reference file on demand.

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
| [`USAGE_EXAMPLES.md`](./USAGE_EXAMPLES.md) | How to organize your world-authoring work: three proven directory layouts (draft→review→finalize, semantic version history, script-assisted optimization) and the command/tool usage that goes with each. |
| [`CLAUDE.md`](./CLAUDE.md) | Project conventions, file structure, pre-commit policy, and the workflow for adding a new platform feature. Loaded automatically into every Claude Code session in this repo. |
| [`DESIGN_BRIEF_v2.md`](./dev-docs/DESIGN_BRIEF_v2.md) | The full design spec the implementation was built against. Architecture rationale, tool surface, validator check list, testing strategy. |
| [`references/WORLD_JSON_SCHEMA_v2.4.md`](./references/WORLD_JSON_SCHEMA_v2.4.md) | Human-readable explanation of every field in the world JSON schema. The canonical JSON Schema artifact lives next to it at `references/world_v2.4.schema.json`. |
| [`example-world-schema-v2.4.json`](./example-world-schema-v2.4.json) | The canonical fixture (schema v2.4). Per design brief §3, this file is the ultimate source of truth — if `validate_world` rejects it, the validator is wrong. [`example-world-schema-v2.2.json`](./example-world-schema-v2.2.json) and [`example-world-schema-v2.1.json`](./example-world-schema-v2.1.json) are retained alongside it as back-compat fixtures (must still validate with only warnings). v2.2 is the one that carries the pre-v2.4 bare-array shape for `triggerPrereqs` / `triggerBlockers`, so it is what proves the validator still reads older worlds. |

## License

MIT. See `.claude-plugin/plugin.json` for the full manifest.
