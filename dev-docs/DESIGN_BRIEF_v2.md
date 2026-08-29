# Infinite Worlds Architect Plugin — Design Brief

**Audience**: a Claude Code session implementing this plugin from scratch.
**Language**: Python 3.12.13. The MCP server uses the official Python `mcp` SDK; schema validation uses the `jsonschema` library.
**Source materials**: this brief (`DESIGN_BRIEF_v2.md`), the schema reference (`WORLD_JSON_SCHEMA_v2.1.md`), and the canonical fixture (`example-world-schema-v2.1.json`). Read them in that order before writing any code.
**Status**: ready for implementation. Items in §9 are deferred work — note them as you encounter them, but do not block on them.

---

## Table of Contents

- [1. Mission](#1-mission)
- [2. Architecture](#2-architecture)
- [3. Source-of-truth principles](#3-source-of-truth-principles)
- [4. Tool surface](#4-tool-surface)
  - [4.1 Inspection](#41-inspection)
  - [4.2 Validation and analysis](#42-validation-and-analysis)
  - [4.3 Helpers](#43-helpers)
  - [4.4 No write tools](#44-no-write-tools)
  - [4.5 Edit-flow contract](#45-edit-flow-contract)
  - [4.6 `validate_world` check list](#46-validate_world-check-list)
- [5. Skills (orchestration prompts)](#5-skills-orchestration-prompts)
  - [5.1 `world-architect`](#51-world-architect)
  - [5.2 `new-world`](#52-new-world)
  - [5.3 `modify-world`](#53-modify-world)
  - [5.4 `spinoff-world`](#54-spinoff-world)
  - [5.5 `sequel-world`](#55-sequel-world)
- [6. Testing strategy](#6-testing-strategy)
  - [6.1 Fixture round-trip](#61-fixture-round-trip)
  - [6.2 Schema coverage test](#62-schema-coverage-test)
  - [6.3 Validator negative tests](#63-validator-negative-tests)
  - [6.4 Coverage threshold](#64-coverage-threshold)
  - [6.5 Fixtures to seek over time](#65-fixtures-to-seek-over-time)
- [7. Implementation milestones](#7-implementation-milestones)
- [8. Repository conventions](#8-repository-conventions)
- [9. Open questions / known unknowns](#9-open-questions--known-unknowns)
- [10. What this brief intentionally does not specify](#10-what-this-brief-intentionally-does-not-specify)

---

## 1. Mission

Infinite Worlds is a third-party storytelling platform. Authors design **worlds** — collections of characters, NPCs, instructions, tracked state, and conditional triggers that the platform uses to run interactive stories with an LLM acting as game master. A world is persisted as a single JSON file conforming to the v2.1 schema documented in `WORLD_JSON_SCHEMA_v2.1.md`.

This plugin assists an author who is building or editing such a world by talking to Claude in a Claude Code session. The plugin's job is to:

- Help the author shape a valid, well-designed world through conversation
- Catch authoring mistakes before the world is sent to the platform
- Provide higher-order analyses (token budgets, trigger-graph cycles, instruction redundancy) the author can act on

**Hard constraints**:

1. The world JSON is the only persistent representation of the world. The plugin never round-trips author content through a different intermediate format.
2. Any JSON the plugin produces must be accepted by the live Infinite Worlds platform. The schema is what the platform actually consumes, not what any human-written document says it should be.
3. Schema knowledge in code lives in exactly one place (the validator), so it can be updated atomically when the platform's schema evolves.

**Non-goals**:

- This plugin is not a UI for editing worlds. The author edits by talking to Claude.
- This plugin does not execute the world (run triggers, evaluate conditions, generate images). The platform does that.
- This plugin is not a story-runtime simulator.

---

## 2. Architecture

The plugin operates in three distinct roles:

### Validator

A single MCP tool, `validate_world`, holds all the plugin's structural knowledge of the schema. It is the authoritative answer to "would the platform accept this world JSON?" Every other tool either defers to it or is independent of schema knowledge entirely. When the platform's schema changes, this is the place that changes.

### Analyst

A small set of MCP tools (`audit_world`, `compare_worlds`, `get_diff_summary`) that perform read-only analyses producing actionable insights. None of them write JSON.

### Helper

A few utilities (`create_new_world_json`, `mint_ids`, `read_world_field`, `format_world_for_review`, `get_schema_summary`, `confirm_path`) that perform small computations the agent shouldn't reproduce by hand each time.

**Writes are not mediated by MCP tools.** The agent edits `world.json` directly using Claude Code's native `Read`, `Edit`, and `Write` tools. The plugin exposes no write tools. This architecture:

- Concentrates schema-shape knowledge in the validator, where it can change atomically
- Makes the JSON file the operational source of truth — the agent reads its shape and edits in place
- Preserves unknown fields naturally (the agent edits one field and leaves the rest alone)
- Keeps the plugin small and robust to schema evolution

The validator catches mistakes; the helpers reduce friction on tasks the agent shouldn't do by hand (ID generation, scaffolding from blank); the analysts provide higher-order intelligence.

---

## 3. Source-of-truth principles

These rules govern every design decision in the plugin. They are non-negotiable.

1. **The fixture is the schema.** `example-world-schema-v2.1.json` is authoritative. `WORLD_JSON_SCHEMA_v2.1.md` is a derived artifact and must be verified against the fixture (and any future fixtures) via the round-trip test in §6.1.

2. **Read before writing.** When the agent edits an existing world, it reads the JSON first and pattern-matches from what's there. When it scaffolds a new world, it uses `create_new_world_json` to produce a known-good starting structure. The agent does not invent field shapes from memory.

3. **Pass-through preservation by default.** Any field the schema doesn't recognize but the platform produces must be preserved exactly when the world is round-tripped. The agent's in-place edit workflow (`Read` then `Edit`) achieves this naturally; the validator's job is to *warn* about unknown fields, not strip them.

4. **`schemaVersion` is load-bearing.** Read it on every world load. Write it on every world write. If a fixture appears with a newer `schemaVersion`, the validator warns loudly and the agent pauses for review.

5. **The schema document is the LLM's reference; the validator is the enforcement.** The fixture is the ultimate ground truth (rule 1): the validator is the codified expression of that truth, and the schema document is a human-readable view of it. If validator and document disagree, the validator wins and the document is updated; if validator and fixture disagree, the validator is wrong and must be fixed to accept the fixture.

---

## 4. Tool surface

All tools take absolute paths for filesystem arguments. All tools that read or write files take a `worldPath`. Tools fail fast with descriptive errors on missing or malformed input. Tools are registered with the MCP SDK's `list_tools` handler in alphabetical order by name.

### 4.1 Inspection

| Tool | Purpose |
|---|---|
| `read_world_field(worldPath, path)` | Read a single field by path. Path syntax supports dotted top-level (`"background"`), name-bracketed entity access (`"NPCs[name=Ada].location"`), and index-bracketed ordered access (`"triggerEvents[0].name"`). Returns the value as JSON-serialized text. |
| `format_world_for_review(worldPath)` | Render the world as a human-readable Markdown document and write it to `<world_stem>.review.md` next to the input world JSON. Returns a JSON envelope: `{"success": "<absolute path>"}` on success, `{"error": "<details>"}` on failure. Writing to disk (instead of returning the markdown directly) keeps the rendered body — which can be thousands of lines on a mature world — out of the calling agent's context window. One-way: the rendered Markdown is not a serialization the plugin reads back. |
| `get_schema_summary()` | Return the canonical schema as structured data — entity types, their fields, field types, allowed enum values. Used by the agent to introspect "what fields exist on a trigger event" without parsing the Markdown schema doc. |

### 4.2 Validation and analysis

| Tool | Purpose |
|---|---|
| `validate_world(worldPath)` | Strict schema check. Reports every error that would cause the platform to reject or misinterpret the world. See §4.6 for the check list. Single authoritative chokepoint for schema knowledge. |
| `audit_world(worldPath)` | Quality and optimization analysis. Token-budget estimates per section, trigger-graph cycle detection, redundancy detection between NPC descriptions and instruction blocks, image-instruction repetition. Produces actionable findings, not pass/fail. (Hard correctness issues like undeclared template-variable references are the validator's job; this tool focuses on quality.) |
| `compare_worlds(worldPathA, worldPathB)` | Structural diff between two worlds. Highlights what changed at every level (entity adds/removes, field changes within entities). |
| `get_diff_summary(originalPath, currentPath)` | Human-readable narrative summary of changes between two worlds — meant for the author to read, not the agent to parse. |

### 4.3 Helpers

| Tool | Purpose |
|---|---|
| `create_new_world_json(outputPath, options)` | Create a fresh world JSON at the given path, populated with sane defaults and an empty-but-validation-passing structure. The single case where the plugin emits schema-shaped content from code. `options` covers things like initial title, NSFW flag, target schema version. |
| `mint_ids(kind, count)` | Generate IDs in the format the platform expects for a given entity kind. `kind` is one of `character`, `npc`, `trackedItem`, `triggerEvent`, `triggerStep` (for trigger conditions/effects), `instructionBlock`. Returns an array of `count` IDs. Format (length, character set, uniqueness scope) is determined by inspecting the canonical fixture — the fixture is the source of truth for what the platform expects. |
| `confirm_path(path)` | Resolve a user-supplied path to an absolute path, verify it exists (or its parent does), and surface it back for confirmation before the agent acts on it. |

### 4.4 No write tools

Per §2, the agent edits world JSON directly through `Read` / `Edit` / `Write`. The plugin exposes no field-level update tools, no entity-level add/modify/remove tools, and no rename/move tools. When friction in the edit flow suggests a write tool would help, the correct response is to invest in the validator's error messages, the schema documentation, or `get_schema_summary` — not to add a write tool.

### 4.5 Edit-flow contract

Because writes go through `Edit`/`Write`, the agent's edit workflow is the load-bearing path. The skill prompts (§5) enforce this contract:

1. **Read** the world (`Read` tool on the JSON file)
2. **Plan** the edit — what field changes, what shape it takes (referencing `get_schema_summary` or the schema doc as needed)
3. **Mint IDs** for any new entities (`mint_ids`)
4. **Edit** the file (`Edit` tool; `Write` only for full-file replacement)
5. **Validate** (`validate_world`)
6. If validation fails, fix and re-validate
7. **Audit** (`audit_world`) before declaring work done on a non-trivial world

### 4.6 `validate_world` check list

The validator must catch at least:

- Wrong types (string where number expected, etc.)
- Missing required fields
- Invalid enum values (effect types, condition types, visibility values, `dataType` values, etc.)
- Broken cross-references: `triggerOnCharacter` referencing a non-existent `characterId`; `effectModifyInstructionBlock.data.id` referencing a non-existent block; `triggerPrereqs`/`triggerBlockers` referencing non-existent trigger IDs
- Duplicate IDs within an array
- Missing or non-unique `positionInList` values within an entity array
- Undeclared template-variable references in text fields (`<<skill_foo>>` where `foo` is not a declared skill; `<<some_item>>` where no matching tracked item exists)
- `schemaVersion` mismatch with the validator's known version (warn, don't fail, on newer versions)
- Cross-field invariants (e.g., `permissionsOnceShared.editing: true` requires `permissionsOnceShared.sharing: true`; `nsfw: true` requires `mature: true`)
- Logic conditions (`category: "logic"`) appearing under a trigger without `advancedLogic: true`
- Unknown top-level keys (warn rather than fail; the validator only reports them — preservation is the agent's responsibility, achieved by reading-then-editing in place)

Validation messages must be precise enough that the agent can fix the issue without further inspection.

---

## 5. Skills (orchestration prompts)

Skills are Markdown prompts in `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`). The LLM activates them based on trigger phrases. Four skills cover the plugin's workflows.

All skill prompts must direct the agent through the edit-flow contract in §4.5. The "field-by-field, wait for approval" cadence is load-bearing UX: the agent shows the user each value being written, waits for "approved" / "looks good" / "next" before moving on, and re-edits when the user says "no, change X."

### 5.1 `world-architect`

Top-level discovery skill. Lists the plugin's capabilities, summarizes the schema, and points the LLM at the other skills. Activated by phrases like "help me build an Infinite Worlds world" or "I want to design a world."

### 5.2 `new-world`

Create a new world from scratch. Workflow:

1. Confirm the output directory and filename with the user (via `confirm_path`)
2. Call `create_new_world_json` to produce a starter JSON
3. Iterate field-by-field with the user — for each field, show the current value, propose changes, wait for approval, then `Edit` the JSON
4. Run `validate_world` after every batch of related edits; fix any reported issues
5. Run `audit_world` before declaring the world done
6. Optionally produce a readable summary with `format_world_for_review`

### 5.3 `modify-world`

Edit an existing world. Workflow:

1. Confirm the world JSON path with the user
2. Read the world; summarize what's in it
3. Ask the user what they want to change
4. For each change: `Edit` the JSON, `validate_world`, surface any issues
5. Run `audit_world` before declaring done

### 5.4 `spinoff-world`

Derive a variant world from an existing one. Workflow:

1. Confirm the source world and the target output path
2. Copy the source JSON to the target
3. Run a `modify-world`-style iteration on the copy, with the agent suggesting variant directions (different setting, different protagonist, different mechanics)
4. Run `validate_world` and `audit_world` on the result
5. Use `compare_worlds` between source and result to summarize what diverged

### 5.5 `sequel-world`

*Added after the v2 design — a port of the original (Node) plugin's sequel capability; see the sequel-world port plan in `claude-scratchpad/sequel-world-work/`.* Build a sequel world from an existing world **plus one or more played story-export `.txt` files**, evolving fields from what actually happened in play. Workflow:

1. Confirm the source world, the story export(s), and the target output path
2. Copy the source to the target via `make_draft_world`
3. Extract the story with `extract_story_data`; query it with `query_story_data` (and optionally `get_character_list` for a character index)
4. Iterate field-by-field, proposing each evolved value with **cited evidence** — optionally enforced by the consent-armed citation-gate `Stop` hook (`hooks/citation_gate.py`)
5. Run `validate_world`, `audit_world`, and `compare_worlds` on the result

The full contract (proposal template, evidence formats, per-field sourcing) lives inline in `commands/sequel-world.md`; general story-extraction-tool usage is in `references/mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md`.

---

## 6. Testing strategy

### 6.1 Fixture round-trip

The single most important test:

```
test_fixture_round_trip(fixture_path):
    world = read_json(fixture_path)
    write_json(temp_path, world)
    written = read_json(temp_path)
    assert structurally_equivalent(world, written)
    assert validate_world(temp_path).errors == []
```

The canonical fixture must JSON-round-trip without loss and pass `validate_world` with zero errors. If `validate_world` reports errors against the fixture, the validator is wrong (per §3 rule 5) and must be corrected to accept the fixture.

This is not a test of the agent's behavior — it's a test of the validator's correctness against the ground-truth fixture.

### 6.2 Schema coverage test

Walk the fixture and verify every top-level key and every nested key the validator's model knows about. Any key in the fixture that the validator doesn't recognize must be reported (preferably as a warning during validation; definitely as a build-time check).

### 6.3 Validator negative tests

For each error class in §4.6, write a small fixture that triggers the error and assert the validator reports it. Wrong effect type name, broken cross-reference, duplicate ID, logic condition under a non-advancedLogic trigger, etc.

### 6.4 Coverage threshold

Aim for 80% line coverage. Most of the plugin's complexity is the validator and its internal schema representation, both easy to cover via fixture-based tests.

### 6.5 Fixtures to seek over time

Each open question in §9 is resolvable by examining an additional fixture (e.g., a world that uses the unverified field). When such a fixture is obtained, add it to the test corpus, extend the validator if needed, and update §9. Do not block implementation on this.

---

## 7. Implementation milestones

Build in this order. Each milestone is a self-contained PR with its own tests passing.

1. **Schema model + validator** — Author the JSON Schema document for the world (`world_v2.1.schema.json`, mirroring `WORLD_JSON_SCHEMA_v2.1.md`) and implement `validate_world` as a two-tier validator. **Tier 1** uses `jsonschema` for structural checks the schema can express declaratively: types, required fields, enum values, basic shape. **Tier 2** is custom Python functions for the constraints `jsonschema` cannot express: cross-references between IDs, undeclared template-variable references, cross-field invariants (e.g., `nsfw → mature`, `editing → sharing`), `schemaVersion` drift detection, and `positionInList` uniqueness. Write the fixture round-trip test (§6.1) and a negative test for each error class. Iterate until the fixture passes with zero errors.
2. **Read tools** — `read_world_field`, `format_world_for_review`, `get_schema_summary`. The schema summary is derived from the same internal representation the validator uses (single source of schema knowledge per §2). Tests against the fixture.
3. **Helper tools** — `create_new_world_json`, `mint_ids`, `confirm_path`. Test that scaffolded output passes the validator and that minted IDs match the fixture's ID format.
4. **Analysis tools** — `audit_world`, `compare_worlds`, `get_diff_summary`. The audit check list can grow over time; start with token budgets and trigger-graph cycles.
5. **Skills** — Author `world-architect`, `new-world`, `modify-world`, `spinoff-world` as Markdown prompts wired to the tool surface and the edit-flow contract.
6. **Plugin packaging** — `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, MCP server entry point. Version 0.1.0.

---

## 8. Repository conventions

> **Update 2026-05-27:** The spawn config originally lived in a top-level `.mcp.json`. That file caused dual-loader warnings (project-scope MCP discovery also picked it up and tried to expand `${CLAUDE_PLUGIN_ROOT}` from Claude Code's own environment, where it is unset). The config is now declared inline in `.claude-plugin/plugin.json` under `mcpServers`; the standalone `.mcp.json` has been removed. References below to `.mcp.json` should be read as "the `mcpServers` block of `plugin.json`".

- **Python**: 3.12.13. Pin via `.python-version` (pyenv) or the equivalent for your chosen environment manager.
- **Plugin manifest**: `.claude-plugin/plugin.json` plus `.claude-plugin/marketplace.json`. Semver bump on every PR.
- **MCP server**: stdio transport via the official `mcp` Python SDK (latest from PyPI). Tools are registered in the SDK's `list_tools` handler and ordered alphabetically by name.
- **`.mcp.json`**: declares the spawn command for the server (e.g., `python -m iw_architect.server`, or via your chosen runner such as `uv run`).
- **Schema validation**: `jsonschema` (PyPI). The validator loads a JSON Schema document (`world_v2.1.schema.json`) that mirrors `WORLD_JSON_SCHEMA_v2.1.md` and ships as a checked-in artifact. Cross-references, template-variable checks, and cross-field invariants layer on top of `jsonschema` as custom Python functions (see §7 milestone 1 for the two-tier validator architecture).
- **Test runner**: `pytest` with `pytest-cov` for coverage.
- **Coverage**: 80% global threshold enforced via `pytest-cov` config in `pyproject.toml`.
- **Pre-commit hook**: the `pre-commit` framework (https://pre-commit.com/) runs tests and lint before each commit.
- **CI**: GitHub Actions runs tests on PRs plus a version-bump check.
- **Path conventions**: `${CLAUDE_PLUGIN_ROOT}` for intra-plugin paths in `.mcp.json` and any hook scripts.
- **Scratchpad**: any temporary files go in `claude-scratchpad/`, which is gitignored.
- **Skills layout**: `skills/<name>/SKILL.md` with YAML frontmatter.
- **Schema artifacts**: keep both the Markdown reference (`WORLD_JSON_SCHEMA_v2.1.md`) and the JSON Schema document (`world_v2.1.schema.json`) inside the plugin's skills tree (e.g., `skills/world-architect/references/`) so the `world-architect` skill can reference both.

See §10 for choices the brief leaves to the implementer.

---

## 9. Open questions / known unknowns

These items are documented in the schema doc. The plugin preserves unknown values verbatim (via read-edit-write) and refuses to emit values for unverified enums/types until a fixture clarifies them.

1. **`illustrationStyle*HighPriority` / `LowPriority`** — semantics versus the older `imageStyle*Pre` / `Post` fields and coexistence rules.
2. **`recommendedAIModel` enum** — fixture has `null`; the platform has AI profiles (e.g., `"smilodon"`). Valid values unverified. *(CLOSED 2026-08-28, Probe E: no import-time enum — IW stores unknown strings verbatim. See `probes/README.md`.)*

---

## 10. What this brief intentionally does not specify

To leave room for the implementer's judgment:

- Package and environment manager (`uv` is recommended for modern Python projects; `pip` + `pyproject.toml` + `venv`, or `poetry`, are also fine)
- Linter / formatter (`ruff` is recommended as a single tool covering both; separate `black` + `flake8` + `isort` also works)
- Static type checker (`mypy` or `pyright`) — optional but recommended
- Internal package layout under `src/iw_architect/` — module split, file naming, etc.
- Exact tokenization rules for `read_world_field`'s path syntax (the syntax in §4.1 is a recommendation, not a spec)
- Specific error message phrasings
- Whether `audit_world` produces findings as Markdown or structured JSON (probably both, controlled by a `format` option)
- Approach for minting the platform's various short ID formats in `mint_ids` — stdlib `uuid.uuid4()` covers the UUID-style IDs for trigger conditions and effects; the 8-character `characterId` / `triggerEvent` IDs and the 9-character entity IDs need a small custom generator. Derive the character set and length for each kind from real fixture samples; do not assume strict alphanumeric (the fixture includes IDs with non-alphanumeric characters)

If any of these choices end up materially shaping the design, surface them in a follow-up question rather than just deciding silently.
