---
description: Edit an existing Infinite Worlds world through a guided field-by-field approval workflow.
argument-hint: "[world_path]"
---

# Modify World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author edit an **existing** Infinite Worlds world JSON. Follow this workflow precisely.

## Recommended reading

The references in `references/` cover authoring judgments worth consulting during modification:

- **When refactoring poor field allocation** (the most common "improve this world" task) → read `references/guidance/FIELD_ALLOCATION_STRATEGY.md`. Typical refactors: moving NPC descriptions out of `background` into `NPCs`, lifting lore from `instructions` into `loreBookEntries`, hoisting state changes into `triggerEvents`. The anti-patterns section names the most common allocation mistakes.
- **When editing any character field** → read `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`. The temptation to "improve" a character by embellishing their dossier is the most common modify-world failure mode. Read the existing dossier first; confirm changes with the author; don't paraphrase away `<<template_variables>>` or details in `names`.
- **When editing `instructions`, `authorStyle`, `descriptionRequest`, or trigger effects** → read `references/mechanics/AI_RUNTIME_MECHANICS.md` to understand what the AI emits each turn before changing the rules that shape it.
- **For per-field judgment calls** → read the matching file in `references/fields/`.

## Step 1 — Confirm the world path

If `$ARGUMENTS` is non-empty, use it as the world path. Otherwise, ask the user for the path.

**Resolve the path to an absolute path before passing it to any MCP world tool** (`confirm_path`, `validate_world`, `read_world_field`, `audit_world`, …). These tools run in a separate MCP server process whose working directory is *not* your session's, so they reject relative paths (a relative path can't be resolved to the file the author means). If the user gave you a relative path, join it with your session's current working directory first — e.g. run `realpath -m "<path>"` (the `-m` resolves paths that don't exist yet; or just take `pwd` and prepend it). A leading `~` is fine; the tools expand it.

Call `confirm_path(path)` with that absolute path. Present the resolved path and confirm the file exists before proceeding.

## Step 2 — Make a working draft copy (never edit the source)

**The source world JSON the author handed you is sacrosanct — never edit it.** It is the clean baseline you will diff your changes against. The *first* thing you do with any existing world is copy it to a draft, and all subsequent work happens on that draft.

1. **Call `make_draft_world(source_path)`** with the confirmed absolute source path — omit the second argument so the tool derives the `_draft` copy. This is the Draft-copy guard from the agent guide above; the tool's own description covers what it does (copies the source untouched, bumps `version`, surfaces it first). Use the `draft_path` it returns for everything below.
2. Call `validate_world(draft_path)` to confirm the copy is clean.

From here on, **every** `Read`, `Edit`, `validate_world`, and `audit_world` call targets the **draft path**. The original source file is never touched again — it stays as the diff baseline.

## Step 3 — Load the draft and ask what to change

1. Call `Read` on the **draft** JSON to load it into context.
2. Ask: "What would you like to change?"

For inspecting a specific field mid-session, use `read_world_field` rather than re-rendering the whole world. Only call `format_world_for_review(draft_path)` if the author explicitly asks for a rendered overview — it is **not** a default step.

## Step 4 — Plan the change

Before touching any file:

- Identify **exactly which fields** will change.
- If adding a new entity (character, NPC, tracked item, trigger, instruction block, lore entry), call `mint_ids(kind, count)` to generate the required IDs.
- If unsure about a field's shape, call `get_schema_summary()` or `read_world_field` to inspect the current value.
- Show the author your plan and wait for approval.

## Step 5 — Edit field-by-field

For **each individual change** (all edits target the **draft**, never the source):

1. **Show** the current value (`read_world_field` or quote from the loaded JSON)
2. **Propose** the new value explicitly
3. **Wait** for the author to approve or revise
4. **Edit** the **draft** JSON with the `Edit` tool — target the specific field, not a full rewrite

## Step 6 — Validate after each batch

After every 3–5 related edits (or immediately after any structural change like adding an entity):

1. Call `validate_world(draft_path)`
2. If there are errors, fix them before continuing and re-validate
3. Never leave the world in an invalid state at the end of a session

## Step 7 — Audit before finishing

Once the author's requested changes are complete:

1. Call `audit_world(draft_path)` and share the findings.
2. Offer to address any warnings the author considers important.

---

## Common change patterns

> All recipes below operate on the **draft path** from Step 2 — `validate_world`, `Edit`, etc. target the draft, never the source.

### Adding a new NPC

> Reference: [`references/fields/OTHER_CHARACTERS.md`](../references/fields/OTHER_CHARACTERS.md) — especially the `one_liner` rule and the `img_appearance`/`img_clothing` author-input requirement.

```
1. mint_ids("npc", 1)           → get the new ID
2. Determine positionInList     → max(existing positions) + 1
3. Edit: append to NPCs array
4. validate_world
```

### Adding a tracked item

> Reference: [`references/fields/TRACKED_ITEMS.md`](../references/fields/TRACKED_ITEMS.md) — dataType / visibility choices, the 10,000-char limit, and what NOT to track. See [`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md) for `dataType: "yaml"`, which is preferred over the deprecated `xml` for new items.

```
1. mint_ids("trackedItem", 1)
2. Determine positionInList
3. Prefer dataType: "yaml"; if yaml, set a unique snake_case variableName (the PawScript $handle)
4. If initialValueBasedOnPC="character", also add initialTrackedItemValues to each character
5. validate_world
```

### Adding a trigger

> Reference: [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md) — when to use which condition and effect type, and the no-automatic-revert rule for world-state replacement effects. See [`references/mechanics/PAWSCRIPT.md`](../references/mechanics/PAWSCRIPT.md) before using the `effectRunScript` effect type.

```
1. mint_ids("triggerEvent", 1)               → trigger ID
2. mint_ids("triggerStep", <conds + effects>) → one distinct UUID per condition AND per effect
3. Build the trigger object — if an effect is effectRunScript, its script may only reference
   existing tracked-item variableNames and must never write to $player/$game
4. Edit: append to triggerEvents array
5. validate_world
```

> `triggerStep` is a synthetic kind that yields UUIDs (the format required for condition/effect `id` fields). Every condition and every effect needs its own distinct UUID — duplicate IDs within the conditions array (or within the effects array) fail validation, and any reused ID makes runtime references ambiguous. Mint one fresh UUID per step.

### Modifying a text field

> Reference: read the matching file in `references/fields/` for the field you're changing before proposing a new value.

```
1. read_world_field(path, "fieldName")   → show current value
2. Propose new value, wait for approval
3. Edit the field in place
4. validate_world
```

---

Use `Edit` (not full `Write`) when changing individual fields, so unknown platform-managed fields survive. Always `Read` before `Edit`, and remember every edit targets the **draft copy** from Step 2 — never the source.
