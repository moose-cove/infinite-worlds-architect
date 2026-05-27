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

## ID formats (derived from canonical fixture)

Always mint IDs with `mint_ids(kind, count)` — never invent them by hand. Formats are entity-specific:

| Entity | ID field | Format |
|---|---|---|
| Player character | `characterId` | 8 chars (`A-Za-z0-9+/`) |
| NPC | `id` | 9 chars (`A-Za-z0-9+/`) |
| Tracked item | `id` | 9 chars |
| Trigger event | `id` | 8 chars |
| Trigger condition / effect | `id` | UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |
| Instruction block | `id` | 9 chars |
| Lore book entry | `id` | 9 chars |
