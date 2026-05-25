---
description: Create a new Infinite Worlds world from scratch using a guided field-by-field workflow.
argument-hint: "[output_path]"
---

# New World

@../../skills/world-architect/SKILL.md

You are guiding an author through creating a brand-new Infinite Worlds story world. Follow this workflow precisely.

## Recommended reading before drafting

The references in `skills/world-architect/references/` cover authoring judgments that affect every step below. Read each on demand, not all upfront:

- **Before drafting `background`, `instructions`, `loreBookEntries`, or `instructionBlocks`** → read `references/FIELD_ALLOCATION_STRATEGY.md`. The most common new-world mistake is packing always-on fields with content that belongs in keyword blocks or trigger effects.
- **Before drafting any character** → read `references/CHARACTER_AUTHORING_GUARDRAILS.md`. New-world authoring has the highest temptation to invent characters to "fill out" the world before the author has decided who they are. Don't — ask the author for every detail and leave blanks where they don't have answers. Always ask for `img_appearance` and `img_clothing` explicitly — never invent them (see `references/CHARACTER_AUTHORING_GUARDRAILS.md` §2 for the canonical formulation).
- **Before drafting `instructions`, `authorStyle`, `descriptionRequest`, or any trigger effect that shapes AI output** → read `references/AI_RUNTIME_MECHANICS.md`. Understanding what the AI emits each turn is the prerequisite for usefully constraining it.
- **Before editing any specific field** → read the matching file in `references/sections/`. Each covers the "what the platform actually does with this field" knowledge that isn't in the schema doc.

## Step 1 — Confirm the output path

If `$ARGUMENTS` is non-empty, use it directly as the output path. Otherwise, ask the user for the path they want to write to.

Call `confirm_path` with the resolved path.

- If the file already exists, warn the user and ask if they want to overwrite.
- If the parent directory doesn't exist, tell the user and stop.
- Present the resolved absolute path and wait for the user to say "yes", "confirmed", or similar before proceeding.

## Step 2 — Scaffold the world

Call `scaffold_world(output_path, title)` with the confirmed path and the user's intended title.

Confirm success, then call `validate_world` to verify the scaffold is clean.

## Step 3 — Iterate field-by-field

For **each field or entity**, follow this loop:

1. **Show** the current value (call `read_world_field` or quote from a recent `Read`)
2. **Propose** a new value based on the author's description
3. **Wait** for the author's approval ("looks good", "yes", "next") or revision ("no, change X to Y")
4. **Edit** the JSON field with the `Edit` tool
5. **Validate** after every 3–5 related edits; fix any errors before continuing

### Suggested field order for a new world

**Core narrative** (do first — see `references/sections/INTRODUCING_THE_STORY.md` and `references/sections/MAIN_INSTRUCTIONS.md`):
- `title`, `description`, `background`, `instructions`, `authorStyle`
- `objective`, `firstInput`

**Maturity and warnings**:
- `mature`, `nsfw`, `contentWarnings`

**Skills** (affects character creation and tracked items):
- `skills` — agree the list before defining characters or tracked items

**Player characters** (`possibleCharacters`) (see `references/sections/PLAYER_CHARACTERS.md`):
- For each character: `name`, `description`, `skills` object
- Mint a `characterId` with `mint_ids("character", 1)`

**NPCs** (see `references/sections/OTHER_CHARACTERS.md`):
- For each NPC: `name`, `one_liner`, `detail`, `appearance`, `location`, `secret_info`, `names`, `img_appearance`, `img_clothing`
- Mint an `id` with `mint_ids("npc", 1)`, assign `positionInList` sequentially

**Tracked items** (see `references/sections/TRACKED_ITEMS.md`):
- For each item: `name`, `dataType`, `visibility`, `description`, `updateInstructions`, `initialValue`, `initialValueBasedOnPC`, `autoUpdate`
- Mint an `id` with `mint_ids("trackedItem", 1)`, assign `positionInList` sequentially

**Triggers** (see `references/sections/TRIGGER_EVENTS.md`):
- For each trigger: `name`, `canTriggerMoreThanOnce`, `advancedLogic`, `triggerOnStartOfGame`, then define conditions and effects
- Mint a trigger `id` with `mint_ids("triggerEvent", 1)`
- Mint condition/effect `id`s with `mint_ids("triggerStep", n)`

**Instruction and lore blocks** (see `references/sections/KEYWORD_INSTRUCTION_BLOCKS.md`):
- For each: `name`, `content`, and `keywords` (lore only)
- Mint `id`s with `mint_ids("instructionBlock", 1)` or `mint_ids("loreBookEntry", 1)`

**Permissions** (optional — defaults are usually fine):
- `allowChangeCharacter*` fields
- `permissionsOnceShared`

**Victory and defeat conditions** (see `references/sections/VICTORY_DEFEAT.md`):
- `victoryCondition`, `defeatCondition`

## Step 4 — Final validation and audit

After the author says they're done with a section:

1. Call `validate_world(world_path)` — fix any reported errors before continuing.
2. Once all content is entered, call `audit_world(world_path)` and present findings to the author.
3. Address any warnings the author cares about.

## Step 5 — Review

Optionally offer to call `format_world_for_review(world_path)` so the author can read a clean summary of the finished world.

---

**Reminder**: Every `Edit` to the JSON must be preceded by a `Read` of the current file content. Never overwrite the file with `Write` unless doing a full replacement — prefer `Edit` to preserve unknown platform-managed fields.
