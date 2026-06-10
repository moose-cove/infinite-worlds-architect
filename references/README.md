# Infinite Worlds reference library

This directory holds authoring and schema references for the `infinite-worlds-architect` plugin. The `world-architect` agent loads files here on demand; human contributors can browse them directly.

## Schema (Tier 1 truth)

| File | Purpose |
|---|---|
| `world_v2.1.schema.json` | The canonical JSON Schema. Used by `validate_world` and the `SCHEMA_SUMMARY` deriver. Authoritative for field shapes, required-ness, enums, and `x-iw-*` semantics. |
| `WORLD_JSON_SCHEMA_v2.1.md` | Human-readable schema walkthrough. Use when the JSON Schema `description` strings are too terse. |

The canonical fixture lives at `example-world-schema-v2.1.json` in the plugin root — ground truth for *real* IW field shapes. If the validator rejects the fixture, the validator is wrong.

## Authoring guidance (read on demand)

| File | Read when |
|---|---|
| `AI_RUNTIME_MECHANICS.md` | Designing `instructions`, `authorStyle`, `descriptionRequest`, any trigger, or any tracked item. **First place to look when something "doesn't fire" or "the AI ignored X".** |
| `FIELD_ALLOCATION_STRATEGY.md` | Populating `background`, `instructions`, `loreBookEntries`, or `instructionBlocks`. Read first when refactoring an existing world. |
| `CHARACTER_AUTHORING_GUARDRAILS.md` | Writing any character. The no-fabrication discipline — never invent `img_appearance` or `img_clothing`. |
| `ADVANCED_METHODOLOGIES.md` | Designing worlds with complex NPC knowledge isolation, perception tiers, or ensemble casts where NPCs must not share information they shouldn't have. |
| `PLATFORM_BEHAVIOR_NOTES.md` | Debugging import issues, understanding IW's canonical JSON field ordering, renaming tracked item / EIB / KIB IDs safely, using the World Debug tools, or using the Export function. |

## Per-field section files

The `sections/` subdirectory contains per-field authoring judgment notes that don't fit in the schema doc.

| File | Covers |
|---|---|
| `sections/INTRODUCING_THE_STORY.md` | `title`, `description`, `background`, `firstInput`, `objective` |
| `sections/MAIN_INSTRUCTIONS.md` | `instructions`, `instructionBlocks`, `authorStyle`, `designNotes`, content flags |
| `sections/PLAYER_CHARACTERS.md` | `skills`, `possibleCharacters`, `allowChangeCharacter*` permissions |
| `sections/OTHER_CHARACTERS.md` | `NPCs` — the critical `one_liner` rule |
| `sections/TRACKED_ITEMS.md` | `trackedItems` (dataType / visibility, the 10,000-char limit, what NOT to track) |
| `sections/TRIGGER_EVENTS.md` | `triggerEvents` (when to use which effect type) |
| `sections/KEYWORD_INSTRUCTION_BLOCKS.md` | `loreBookEntries` (substring matching, the awareness paradox) |
| `sections/VICTORY_DEFEAT.md` | `victoryCondition` / `defeatCondition` |
| `sections/IMAGE_STYLE.md` | `imageStyle*`, `illustrationStyle*`, LoRA keywords, model word limits |
| `sections/MISC_ADVANCED_FEATURES.md` | `descriptionRequest`, `summaryRequest`, Summary AI cadence |
| `sections/WORLD_DESIGN_PATTERNS.md` | Reusable `trackedItems` + `instructionBlocks` architectural patterns: phase escalation, survival stats, word-count control, NPC appearance caching. |
| `sections/IMAGE_SYSTEM_PATTERNS.md` | Advanced image consistency techniques: persistent attribute storage, exact-string tables, multi-pass validation, field isolation. Read alongside `IMAGE_STYLE.md`. |
| `sections/INSTRUCTION_BLOCK_TEMPLATES.md` | Ready-to-use EIB (`instructionBlock`) content templates: AI Taming, Claude Taming, Dialogue Integrity, pacing, characterization. |

## Authoring-intent → section-file lookup

Use this when the author's request doesn't map obviously to a field name:

| When the author asks about… | Load this file |
|---|---|
| Opening scene, premise, title, first action | `sections/INTRODUCING_THE_STORY.md` |
| AI behavior, writing style, instructions | `sections/MAIN_INSTRUCTIONS.md` |
| Player characters, skills, character switching | `sections/PLAYER_CHARACTERS.md` |
| NPCs, adding/editing characters | `sections/OTHER_CHARACTERS.md` |
| Tracked items, inventory, game-state variables | `sections/TRACKED_ITEMS.md` |
| Triggers, conditional events, "when X happens", "end when dragon dies" | `sections/TRIGGER_EVENTS.md` |
| Lore, faction backstory, location info, keyword injection | `sections/KEYWORD_INSTRUCTION_BLOCKS.md` |
| Victory, defeat, ending the game | `sections/VICTORY_DEFEAT.md` |
| Illustration style, image generation, LoRAs | `sections/IMAGE_STYLE.md` |
| Summary AI, description format, advanced mechanics | `sections/MISC_ADVANCED_FEATURES.md` |
| Phase escalation, survival stats, word count control, NPC caching | `sections/WORLD_DESIGN_PATTERNS.md` |
| Image consistency, attribute drift, exact-string tables, field isolation | `sections/IMAGE_SYSTEM_PATTERNS.md` |
| EIB templates, AI taming, dialogue integrity, pacing | `sections/INSTRUCTION_BLOCK_TEMPLATES.md` |
| NPC omniscience, knowledge isolation, perception tiers | `ADVANCED_METHODOLOGIES.md` |
| Import behavior, ID renaming, JSON field order, World Debug, Export | `PLATFORM_BEHAVIOR_NOTES.md` |

## ID formats (charsets from the canonical fixture; length bounds from KB import testing)

Always mint IDs with `mint_ids(kind, count)` — never invent them by hand. Formats are entity-specific:

| Entity | ID field | Format |
|---|---|---|
| Player character | `characterId` | 8 chars (`A-Za-z0-9+/`) |
| NPC | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |
| Tracked item | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |
| Trigger event | `id` | 8 chars |
| Trigger condition / effect | `id` | UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |
| Instruction block | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |
| Lore book entry | `id` | max 9 chars (`A-Za-z0-9+/`) [^idlen] |

[^idlen]: **KB-empirical.** The canonical fixture only contains 9-char IDs, so the fixture alone reads as "exactly 9." KB import testing confirms shorter IDs (1–9 chars) are valid for these four entity kinds — the rule is a *maximum*, not a fixed length.
