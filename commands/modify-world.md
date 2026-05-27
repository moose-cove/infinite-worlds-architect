---
description: Edit an existing Infinite Worlds world through a guided field-by-field approval workflow.
argument-hint: "[world_path]"
---

# Modify World

@../../agents/world-architect.md

You are helping an author edit an **existing** Infinite Worlds world JSON. Follow this workflow precisely.

## Recommended reading

The references in `references/` cover authoring judgments worth consulting during modification:

- **When refactoring poor field allocation** (the most common "improve this world" task) → read `references/FIELD_ALLOCATION_STRATEGY.md`. Typical refactors: moving NPC descriptions out of `background` into `NPCs`, lifting lore from `instructions` into `loreBookEntries`, hoisting state changes into `triggerEvents`. The anti-patterns section names the most common allocation mistakes.
- **When editing any character field** → read `references/CHARACTER_AUTHORING_GUARDRAILS.md`. The temptation to "improve" a character by embellishing their dossier is the most common modify-world failure mode. Read the existing dossier first; confirm changes with the author; don't paraphrase away `<<template_variables>>` or details in `names`.
- **When editing `instructions`, `authorStyle`, `descriptionRequest`, or trigger effects** → read `references/AI_RUNTIME_MECHANICS.md` to understand what the AI emits each turn before changing the rules that shape it.
- **For per-field judgment calls** → read the matching file in `references/sections/`.

## Step 1 — Confirm the world path

If `$ARGUMENTS` is non-empty, use it directly as the world path. Otherwise, ask the user for the path.

Call `confirm_path(path)` with the resolved path. Present the resolved path and confirm the file exists before proceeding.

## Step 2 — Summarize the current world

1. Call `Read` on the world JSON to load it into context.
2. Call `format_world_for_review(world_path)` and present a concise summary to the author.
3. Ask: "What would you like to change?"

## Step 3 — Plan the change

Before touching any file:

- Identify **exactly which fields** will change.
- If adding a new entity (character, NPC, tracked item, trigger, instruction block, lore entry), call `mint_ids(kind, count)` to generate the required IDs.
- If unsure about a field's shape, call `get_schema_summary()` or `read_world_field` to inspect the current value.
- Show the author your plan and wait for approval.

## Step 4 — Edit field-by-field

For **each individual change**:

1. **Show** the current value (`read_world_field` or quote from the loaded JSON)
2. **Propose** the new value explicitly
3. **Wait** for the author to approve or revise
4. **Edit** the JSON with the `Edit` tool — target the specific field, not a full rewrite

## Step 5 — Validate after each batch

After every 3–5 related edits (or immediately after any structural change like adding an entity):

1. Call `validate_world(world_path)`
2. If there are errors, fix them before continuing and re-validate
3. Never leave the world in an invalid state at the end of a session

## Step 6 — Audit before finishing

Once the author's requested changes are complete:

1. Call `audit_world(world_path)` and share the findings.
2. Offer to address any warnings the author considers important.

---

## Common change patterns

### Adding a new NPC

> Reference: [`references/sections/OTHER_CHARACTERS.md`](../references/sections/OTHER_CHARACTERS.md) — especially the `one_liner` rule and the `img_appearance`/`img_clothing` author-input requirement.

```
1. mint_ids("npc", 1)           → get the new ID
2. Determine positionInList     → max(existing positions) + 1
3. Edit: append to NPCs array
4. validate_world
```

### Adding a tracked item

> Reference: [`references/sections/TRACKED_ITEMS.md`](../references/sections/TRACKED_ITEMS.md) — dataType / visibility choices, the 10,000-char limit, and what NOT to track.

```
1. mint_ids("trackedItem", 1)
2. Determine positionInList
3. If initialValueBasedOnPC="character", also add initialTrackedItemValues to each character
4. validate_world
```

### Adding a trigger

> Reference: [`references/sections/TRIGGER_EVENTS.md`](../references/sections/TRIGGER_EVENTS.md) — when to use which condition and effect type, and the no-automatic-revert rule for world-state replacement effects.

```
1. mint_ids("triggerEvent", 1)           → trigger ID
2. mint_ids("triggerStep", n)            → IDs for conditions and effects
3. Build the trigger object
4. Edit: append to triggerEvents array
5. validate_world
```

### Modifying a text field

> Reference: read the matching file in `references/sections/` for the field you're changing before proposing a new value.

```
1. read_world_field(path, "fieldName")   → show current value
2. Propose new value, wait for approval
3. Edit the field in place
4. validate_world
```

---

**Reminder**: Always use `Edit` (not full `Write`) when changing individual fields, to preserve unknown platform-managed fields. Always `Read` before `Edit`.
