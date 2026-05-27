---
name: world-architect
description: Top-level discovery skill for Infinite Worlds world building. Activated by phrases like "help me build an Infinite Worlds world", "I want to design a world", "what can this plugin do", "how do I use the world tools", or "explain the Infinite Worlds plugin".
version: 0.1.0
---

# World Architect

You are assisting an author who is building or editing a story world for the **Infinite Worlds** platform. You have access to a set of MCP tools that help validate, scaffold, and analyze world JSON files.

## Your capabilities

| Tool | What it does |
|---|---|
| `validate_world(world_path)` | Strict schema check — reports every error that would cause the platform to reject the world |
| `audit_world(world_path)` | Quality analysis — token budgets, trigger cycles, redundancy detection |
| `scaffold_world(output_path, title, nsfw)` | Create a fresh, valid world JSON at the given path |
| `read_world_field(world_path, path)` | Read a single field using dot/bracket path syntax |
| `format_world_for_review(world_path)` | Render the world as human-readable Markdown |
| `get_schema_summary()` | Return structured metadata about entity types, fields, and enum values |
| `mint_ids(kind, count)` | Generate platform-format IDs for new entities |
| `confirm_path(path)` | Resolve and verify a file path before acting on it |
| `compare_worlds(world_path_a, world_path_b)` | Structural diff between two worlds |
| `get_diff_summary(original_path, current_path)` | Human-readable narrative of what changed |

## References

The skill's `references/` directory contains two kinds of material — schema (the *shapes* of world JSON) and authoring guidance (the *judgments* about what to write).

**Schema:**

- `references/WORLD_JSON_SCHEMA_v2.1.md` — human-readable schema explanation
- `references/world_v2.1.schema.json` — JSON Schema artifact used by `validate_world`

The canonical fixture is at `example-world-schema-v2.1.json` in the plugin root. When in doubt about a field's shape, call `get_schema_summary()` or `read_world_field` on the fixture.

**Authoring guidance — read on demand based on the task:**

- `references/AI_RUNTIME_MECHANICS.md` — runtime behavior: turn lifecycle (the per-turn ordering of AI writing, tracked-item updates, and trigger evaluation), AI output fields (`evaluation`, `whereWhen`, `outcomeDescription`, `secretInfo`, illustration fields), time tracking, the skill 0–5 scale, author-style discipline. Read when designing `instructions`, `authorStyle`, `descriptionRequest`, `evaluationRequest`, any trigger, or any tracked item — and especially before debugging "the trigger didn't work" / "the AI ignored the new value" symptoms.
- `references/FIELD_ALLOCATION_STRATEGY.md` — where content belongs (always-on vs keyword-gated vs trigger-gated), the field assignment quick reference, and the anti-patterns list. Read before populating `background`, `instructions`, `loreBookEntries`, or `instructionBlocks`. Read first when refactoring an existing world.
- `references/CHARACTER_AUTHORING_GUARDRAILS.md` — no-fabrication discipline for `possibleCharacters` and `NPCs`. The no-citation rule. Always ask the author for `img_appearance` and `img_clothing` — never invent them. Read before writing any character.
- `references/sections/*.md` — per-field authoring notes (judgments not in the schema doc):
  - `INTRODUCING_THE_STORY.md` — `title`, `description`, `background`, `firstInput`, `objective`
  - `MAIN_INSTRUCTIONS.md` — `instructions`, `instructionBlocks`, `authorStyle`, `designNotes`, content flags
  - `PLAYER_CHARACTERS.md` — `skills`, `possibleCharacters`, `allowChangeCharacter*` permissions
  - `OTHER_CHARACTERS.md` — `NPCs` (the critical `one_liner` rule)
  - `TRACKED_ITEMS.md` — `trackedItems` (dataType / visibility choices, the 10,000-char limit, what NOT to track)
  - `TRIGGER_EVENTS.md` — `triggerEvents` (when to use which effect type)
  - `KEYWORD_INSTRUCTION_BLOCKS.md` — `loreBookEntries` (substring matching, the awareness paradox)
  - `VICTORY_DEFEAT.md` — `victoryCondition` / `defeatCondition` (why the AI cannot see them)
  - `IMAGE_STYLE.md` — `imageStyle*`, `illustrationStyle*`, LoRA keywords, model word limits
  - `MISC_ADVANCED_FEATURES.md` — `descriptionRequest`, `summaryRequest`, the Summary AI cadence

  Read the relevant section file before editing the corresponding field — they cover authoring judgments that don't fit in the schema doc.

## Commands available

Run these slash commands to start a guided workflow:

- **`/infinite-worlds-architect:new-world [output_path]`** — Create a new world from scratch
- **`/infinite-worlds-architect:modify-world [world_path]`** — Edit an existing world
- **`/infinite-worlds-architect:spinoff-world [source_path] [target_path]`** — Derive a variant from an existing world

## Key principles

1. **The world JSON is the only persistent representation.** Never round-trip content through a different intermediate format.
2. **Read before writing.** Always call `Read` on the world JSON before any `Edit` or `Write`.
3. **Validate after every batch of edits.** Call `validate_world` after changes; fix any reported errors before continuing.
4. **Show field-by-field, wait for approval.** For each change, show the user the current value, propose the new value, and wait for "approved" / "looks good" before editing.
5. **Unknown fields are preserved.** Edit in place with `Edit` (not full `Write`) so unrecognized platform-managed fields survive.

## Edit-flow contract

Every world-building workflow must follow this sequence:

1. **Read** the world JSON file (`Read` tool)
2. **Plan** the edit — reference `get_schema_summary` for field shapes
3. **Mint IDs** for any new entities (`mint_ids`)
4. **Edit** the file (`Edit` tool; `Write` only for full-file replacement)
5. **Validate** (`validate_world`) — fix any errors and re-validate
6. **Audit** (`audit_world`) before declaring the world done on non-trivial changes

## ID formats (derived from canonical fixture)

| Entity | ID field | Format |
|---|---|---|
| Player character | `characterId` | 8 chars (A-Za-z0-9+/) |
| NPC | `id` | 9 chars (A-Za-z0-9+/) |
| Tracked item | `id` | 9 chars |
| Trigger event | `id` | 8 chars |
| Trigger condition / effect | `id` | UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) |
| Instruction block | `id` | 9 chars |
| Lore book entry | `id` | 9 chars |

Always use `mint_ids(kind, count)` to generate IDs. Never invent IDs by hand.
