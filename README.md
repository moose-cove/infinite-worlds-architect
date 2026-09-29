# Infinite Worlds Architect

A Claude Code and Codex plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds through conversation. It includes MCP tools for validating and analyzing world JSON, plus guided authoring workflows.

## What this is

Infinite Worlds is a third-party storytelling platform where authors design **worlds** — collections of characters, NPCs, instructions, tracked state, and conditional triggers that the platform uses to run interactive stories. A world is persisted as a single JSON file conforming to the v2.4 schema documented in [`references/WORLD_JSON_SCHEMA_v2.4.md`](./references/WORLD_JSON_SCHEMA_v2.4.md).

This plugin assists an author who is building or editing such a world in Codex or Claude Code. The plugin:

- Validates world JSON against the platform's schema before sending it live
- Scaffolds new worlds from sane defaults
- Audits quality (token budgets, trigger cycles, redundancy detection)
- Searches Community Worlds, reads descriptions, and retrieves original world JSON
- Provides a Claude `world-architect` agent and four guided slash commands, plus matching Codex skills

The plugin has **no write tools**. The assistant edits world JSON with its normal file tools; the MCP server validates and analyzes it.

## Community Worlds login and search

From the plugin directory, sign in locally:

```bash
uv run iw-community-auth login
```

The command prompts for your Infinite Worlds email and password in the terminal, then stores the credentials and session in the system keychain. When the site session expires, the plugin signs in again. The credentials are never entered into a chat or stored in the plugin source. Run `uv run iw-community-auth status` to check the session, or `uv run iw-community-auth logout` to remove the local credentials.

If you already have a signed-in Chrome window launched with `--remote-debugging-port=9222`, you can import its session without entering a password:

```bash
uv run iw-community-auth import-chrome --port 9222
```

An imported session works until it expires. Use `login` for automatic renewal. Community tools connect directly to Infinite Worlds over HTTP and WebSocket; they do not control Chrome. You can ask for a text search, included tags that must all match or may match any, excluded tags, mature or NSFW filters, a sort order, and a page. `get_community_world_details` returns the full catalog description. `get_community_world_json` returns the original world JSON, which the assistant can save as a file using its normal file tools. Reading a world does not copy it into your Infinite Worlds account.

These calls use Infinite Worlds' internal Anvil protocol. If the site changes that protocol, the community tools may need an update.

## Install in Codex and the ChatGPT desktop app

Install [`uv`](https://docs.astral.sh/uv/) first. From a terminal, register this checkout as a local marketplace and install the plugin:

```bash
codex plugin marketplace add /absolute/path/to/infinite-worlds-architect
codex plugin add infinite-worlds-architect@iw-architect-local
```

The marketplace entry lives in [`.agents/plugins/marketplace.json`](./.agents/plugins/marketplace.json). The Codex manifest is [`.codex-plugin/plugin.json`](./.codex-plugin/plugin.json), and [`.mcp.json`](./.mcp.json) starts `iw-json-tools` from the plugin root with `cwd: "."`. In the Plugins Directory, find **Infinite Worlds Architect**. It contributes the `world-architect`, `new-world`, `modify-world`, `spinoff-world`, and `sequel-world` skills.

## Install in Claude Code

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
| `search_community_worlds(...)` | Search text across title, description, and author; include or exclude tags; filter mature and NSFW worlds; sort and paginate. |
| `get_community_world_details(world_id)` | Read one community world's complete catalog description and metadata by code or UUID. |
| `get_community_world_json(world_id)` | Read the original world JSON by code or UUID without making a copy in the account. |

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
