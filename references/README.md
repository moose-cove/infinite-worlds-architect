# Infinite Worlds reference library

This directory holds authoring and schema references for the `infinite-worlds-architect` plugin. The `world-architect` agent loads files here on demand; human contributors can browse them directly.

## Schema (Tier 1 truth)

| File | Purpose |
|---|---|
| `world_v2.4.schema.json` | The canonical JSON Schema. Used by `validate_world` and the `SCHEMA_SUMMARY` deriver. Authoritative for field shapes, required-ness, enums, and `x-iw-*` semantics. |
| `WORLD_JSON_SCHEMA_v2.4.md` | Human-readable schema walkthrough. Use when the JSON Schema `description` strings are too terse. |

The canonical fixture lives at `example-world-schema-v2.4.json` in the plugin root — ground truth for *real* IW field shapes. If the validator rejects the fixture, the validator is wrong. (`example-world-schema-v2.2.json` and `example-world-schema-v2.1.json` are retained alongside it as back-compat fixtures — not canonical; they must still validate with only warnings.)

## `mechanics/` — Runtime and platform behaviour

| File | Read when |
|---|---|
| `mechanics/AI_RUNTIME_MECHANICS.md` | Designing `instructions`, `authorStyle`, `descriptionRequest`, any trigger, or any tracked item. **First place to look when something "doesn't fire" or "the AI ignored X".** |
| `mechanics/PAWSCRIPT.md` | Writing `<<…>>` expressions beyond a bare variable name, or authoring an `effectRunScript` script. Covers expressions vs. scripts, native `$player`/`$game` variables, the statement set, bounded loops, transactional execution, and the function cheat-sheet. |
| `mechanics/PLATFORM_BEHAVIOR_NOTES.md` | Debugging import issues, understanding IW's canonical JSON field ordering, renaming tracked item / EIB / KIB IDs safely, using the World Debug tools, or using the Export function. |
| `mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md` | Reading a played story with the `extract_story_data` / `query_story_data` / `get_character_list` tools — the tiered loading sequence and the `turn_detail` query budget. For any agent that needs to inspect a story export (e.g. a `modify-world` agent checking how a change played out), not only `sequel-world`. |

## `guidance/` — Authoring principles

| File | Read when |
|---|---|
| `guidance/FIELD_ALLOCATION_STRATEGY.md` | Populating `background`, `instructions`, `loreBookEntries`, or `instructionBlocks`. Read first when refactoring an existing world. |
| `guidance/CHARACTER_AUTHORING_GUARDRAILS.md` | Writing any character. The no-fabrication discipline — ground every detail in author input or a source, never genre tropes. |
| `guidance/LAYERED_KNOWLEDGE_ISOLATION.md` | Designing worlds with complex NPC knowledge isolation, perception tiers, or ensemble casts where NPCs must not share information they shouldn't have. |

## `fields/` — Per-field authoring judgment notes

| File | Covers |
|---|---|
| `fields/INTRODUCING_THE_STORY.md` | `title`, `description`, `background`, `firstInput`, `objective` |
| `fields/MAIN_INSTRUCTIONS.md` | `instructions`, `instructionBlocks`, `authorStyle`, `designNotes`, content flags |
| `fields/PLAYER_CHARACTERS.md` | `skills`, `possibleCharacters`, `allowChangeCharacter*` permissions |
| `fields/OTHER_CHARACTERS.md` | `NPCs` — the critical `one_liner` rule |
| `fields/TRACKED_ITEMS.md` | `trackedItems` (dataType / visibility, the 10,000-char limit, what NOT to track) |
| `fields/YAML_TRACKED_ITEMS.md` | Structured tracked items: `dataType: "yaml"` (XML deprecated), `variableName`, `formatSchema` / `formatExample` / `enforceFormat`, YAML quoting gotchas, the puppy-tracker worked example |
| `fields/TRIGGER_EVENTS.md` | `triggerEvents` (when to use which effect type) |
| `fields/KEYWORD_INSTRUCTION_BLOCKS.md` | `loreBookEntries` (substring matching, the awareness paradox) |
| `fields/VICTORY_DEFEAT.md` | `victoryCondition` / `defeatCondition` |
| `fields/IMAGE_STYLE.md` | `imageStyle*`, `illustrationStyle*`, LoRA keywords, model word limits |
| `fields/MISC_ADVANCED_FEATURES.md` | `descriptionRequest`, `summaryRequest`, Summary AI cadence |

## `patterns/` — Reusable design patterns

Recurring architectural patterns from real IW world builds. Each pattern can be applied independently; they compose without conflict.

| File | Covers |
|---|---|
| `patterns/IMAGE_SYSTEM_PATTERNS.md` | Advanced image consistency techniques: persistent attribute storage, exact-string tables, multi-pass validation, field isolation. Read alongside `fields/IMAGE_STYLE.md`. |
| `patterns/PHASE_ESCALATION.md` | Pattern: use `effectModifyInstructionBlock` to swap an EIB's content at story beats, driving multi-phase world-state escalation. |
| `patterns/SURVIVAL_STATS.md` | Pattern: single `text` TI with holistic numerical update rules for survival stat sets (Hunger, Thirst, Stamina, etc.). |
| `patterns/TARGET_WORD_COUNT.md` | Pattern: player-adjustable `number` TI driving turn-length control via `<<>>` math expressions in `instructions`. |
| `patterns/NPC_APPEARANCE_CACHE.md` | Pattern: `ai_only` `text` TI as a rolling cache of NPC visual descriptions for consistent image generation across turns. |

## `templates/` — Ready-to-use instruction block content

| File | Covers |
|---|---|
| `templates/AI_TAMING.md` | Ready-to-use EIB: general AI defaults (omniscience, infallibility, jargon, authority-calling). Copy and adapt. |
| `templates/CLAUDE_TAMING.md` | Ready-to-use EIB: Claude-family model taming (omniscient NPCs, generic names, surveillance forces). Apply to all `-thinking` variants. |
| `templates/DIALOGUE_INTEGRITY.md` | Ready-to-use EIB: forbid comparative flattery, manufactured rapport, and unearned information-sharing in NPC dialogue. |
| `templates/CLAUDE_BUGFIXES.md` | Ready-to-use EIB (lighter): restricts `secretInfo` misuse and psychobabble for Claude-family models. |
| `templates/TURN_BASED_PACING.md` | Ready-to-use EIB: prevents scene-rushing and missing player-interactive moments in turn-based play. |
| `templates/QOL_CHARACTERIZATION.md` | Ready-to-use EIB: prevents NPC character degradation (mindless vessels, out-of-character reactions after failed checks). |
| `templates/USAGE_NOTES.md` | Cross-cutting notes on EIB token length, `selectedAIProfiles` gating, and legacy "Lion" naming. |

## Authoring-intent → file lookup

Use this when the author's request doesn't map obviously to a field name:

| When the author asks about… | Load this file |
|---|---|
| Opening scene, premise, title, first action | `fields/INTRODUCING_THE_STORY.md` |
| AI behavior, writing style, instructions | `fields/MAIN_INSTRUCTIONS.md` |
| Player characters, skills, character switching | `fields/PLAYER_CHARACTERS.md` |
| NPCs, adding/editing characters | `fields/OTHER_CHARACTERS.md` |
| Tracked items, inventory, game-state variables | `fields/TRACKED_ITEMS.md` |
| YAML / structured tracked items, `variableName`, `formatSchema`, `enforceFormat` | `fields/YAML_TRACKED_ITEMS.md` |
| PawScript, `<<…>>` expressions, `effectRunScript` scripts, `$player`/`$game`, `.count()`/`.where()` | `mechanics/PAWSCRIPT.md` |
| Triggers, conditional events, "when X happens", "end when dragon dies" | `fields/TRIGGER_EVENTS.md` |
| Lore, faction backstory, location info, keyword injection | `fields/KEYWORD_INSTRUCTION_BLOCKS.md` |
| Victory, defeat, ending the game | `fields/VICTORY_DEFEAT.md` |
| Illustration style, image generation, LoRAs | `fields/IMAGE_STYLE.md` |
| Summary AI, description format, advanced mechanics | `fields/MISC_ADVANCED_FEATURES.md` |
| Phase escalation, swapping world state via EIB replacement | `patterns/PHASE_ESCALATION.md` |
| Survival stats, holistic stat tracking in a single TI | `patterns/SURVIVAL_STATS.md` |
| Word count control, turn length, paragraph count | `patterns/TARGET_WORD_COUNT.md` |
| NPC appearance caching, consistent image generation across turns | `patterns/NPC_APPEARANCE_CACHE.md` |
| Image consistency, attribute drift, exact-string tables, field isolation | `patterns/IMAGE_SYSTEM_PATTERNS.md` |
| AI taming, omniscient NPCs, jargon, authority-calling | `templates/AI_TAMING.md` |
| Claude taming, generic names, surveillance forces, Claude-family EIBs | `templates/CLAUDE_TAMING.md` |
| Dialogue integrity, comparative flattery, manufactured rapport, NPC voice | `templates/DIALOGUE_INTEGRITY.md` |
| Claude bugfixes, secretInfo misuse, psychobabble, lighter Claude EIB | `templates/CLAUDE_BUGFIXES.md` |
| Turn-based pacing, scene rushing, player-interactive moments | `templates/TURN_BASED_PACING.md` |
| Character degradation, mindless vessels, out-of-character reactions | `templates/QOL_CHARACTERIZATION.md` |
| EIB length, selectedAIProfiles, token budget, model-gating | `templates/USAGE_NOTES.md` |
| NPC omniscience, knowledge isolation, perception tiers | `guidance/LAYERED_KNOWLEDGE_ISOLATION.md` |
| Import behavior, ID renaming, JSON field order, World Debug, Export | `mechanics/PLATFORM_BEHAVIOR_NOTES.md` |
| Sequel world building, continuing a story, evidence citation, no-fabrication for sequels | `/infinite-worlds-architect:sequel-world` command (carries the citation + sourcing discipline inline) |
| Reading/inspecting a played story, story extraction tools, query strategy/budget | `mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md` |

## ID formats (charsets from the canonical fixture; length bounds from KB import testing)

Always mint IDs with `mint_ids(kind, count)` — never invent them by hand. Formats are entity-specific:

| Entity | ID field | Format |
|---|---|---|
| Player character | `characterId` | 8 chars (`A-Za-z0-9+/`) |
| NPC | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |
| Tracked item | `id` | max 9 chars, **alphanumeric only** (`A-Za-z0-9`) [^idlen] [^trkid] |
| Tracked item | `variableName` | snake_case, **unique**; derived from the item's `name`. **Not minted** — it is the PawScript handle addressed as `$<variableName>`. [^varname] |
| Trigger event | `id` | 8 chars |
| Trigger condition / effect | `id` | UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |
| Instruction block | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |
| Lore book entry | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |

[^idlen]: **KB-empirical.** The canonical fixture only contains 9-char IDs, so the fixture alone reads as "exactly 9." KB import testing confirms shorter IDs (1–9 chars) are valid for these four entity kinds — the rule is a *maximum*, not a fixed length.

[^trkid]: **KB-empirical — June 2026 import test.** IW silently renames tracked-item IDs that contain `+`, `/`, or other non-alphanumeric characters to random 9-char alphanumeric strings on import, WITHOUT updating trigger references (dangling refs, broken triggers). EIB/KIB/trigger-event IDs with `+`/`/` survived the same test unchanged — the hazard is specific to `trackedItems[].id`. `mint_ids` now emits alphanumeric-only IDs for all entity kinds.

[^varname]: `variableName` is a v2.2 tracked-item field, distinct from the opaque `id`. It is **not** minted by `mint_ids` — it's a human-readable snake_case symbol the author (or platform) derives from the item's `name`, and it must be unique because PawScript addresses the item by it as `$<variableName>`. See [`fields/YAML_TRACKED_ITEMS.md`](./fields/YAML_TRACKED_ITEMS.md) and [`mechanics/PAWSCRIPT.md`](./mechanics/PAWSCRIPT.md).
