---
description: Derive a variant world from an existing Infinite Worlds world, keeping the original intact.
argument-hint: "[source_path] [target_path]"
---

# Spinoff World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author create a **variant** of an existing Infinite Worlds world — keeping the original intact and producing a new divergent version.

## Recommended reading

The references in `references/` cover authoring judgments specific to spinoffs:

- **Before changing any character** → read `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`. Spinoffs especially benefit from the no-fabrication rule because the temptation is to "complete" thinly-sketched source characters by inventing detail. The source dossier is the floor, not a starting point to embellish. Premise changes don't license character changes — ask the author what carries forward and what doesn't.
- **When deciding whether to keep or restructure source content** → read `references/guidance/FIELD_ALLOCATION_STRATEGY.md`. A spinoff with a different premise often needs content reallocated (e.g., the original's `background` describes the wrong setting; some of its `instructionBlocks` become irrelevant). Use the allocation rules to decide what to keep, what to move, and what to drop.
- **When changing `instructions`, `authorStyle`, or any trigger that the spinoff inherits** → read `references/mechanics/AI_RUNTIME_MECHANICS.md` to understand what those fields actually shape at runtime.
- **For per-field judgment calls** → read the matching file in `references/fields/`.

## Step 1 — Confirm paths

If `$ARGUMENTS` contains two paths (source then target, space-separated), use them. Otherwise, ask the user for each path in turn.

**Resolve every path to an absolute path before passing it to any MCP world tool** (`confirm_path`, `compare_worlds`, `get_diff_summary`, …). These tools run in a separate MCP server process whose working directory is *not* your session's, so they reject relative paths (a relative path can't be resolved to the file the author means). If the user gave you a relative path, join it with your session's current working directory first — e.g. run `realpath -m "<path>"` (the `-m` resolves the not-yet-created target path; or just take `pwd` and prepend it). A leading `~` is fine; the tools expand it.

1. Call `confirm_path` on the **source** world path (absolute). It must exist.
2. Ask the user for the **target** output path for the variant (if not supplied via arguments).
3. Call `confirm_path` on the target path. Its parent must exist; warn if the file already exists.
4. Present both resolved paths and wait for confirmation before proceeding.

## Step 2 — Copy the source to the variant target (via `make_draft_world`)

**Never modify the source world.** Call `make_draft_world(source_path, target_path)` with both absolute paths — pass the author's chosen `target_path` from Step 1 explicitly, so the tool copies there (the spinoff exception noted in the Draft-copy guard above) instead of deriving a `_draft` name. The tool's own description covers what it does (copies the source untouched, bumps `version`, surfaces it first).

Then call `validate_world(target_path)` to confirm the copy is clean.

## Step 3 — Suggest variant directions

Offer the author 3–5 concrete directions the variant could take. For example:

- **Different setting** — same characters, different world or era
- **Different protagonist** — same world, new lead character with a contrasting background
- **Tonal shift** — e.g., a cozy version of a grim world, or vice versa
- **Different mechanics** — changed tracked items, new skill system, altered trigger logic
- **Story fork** — begins at a pivotal moment from the source world and takes a different path

Let the author choose or describe their own direction.

## Step 4 — Iterate changes on the copy

Follow the **modify-world** field-by-field approval loop on the target file:

1. Show current value
2. Propose change
3. Wait for approval
4. Edit
5. Validate after each batch

Key fields that usually diverge in a spinoff (read the matching file in `references/fields/` before drafting changes):
- `title`, `description`, `background` (see [`references/fields/INTRODUCING_THE_STORY.md`](../references/fields/INTRODUCING_THE_STORY.md)) — identify the variant clearly
- `designNotes` (see [`references/fields/MAIN_INSTRUCTIONS.md`](../references/fields/MAIN_INSTRUCTIONS.md)) — record why this variant exists (not sent to AI)
- Character `name` and `description` (see [`references/fields/PLAYER_CHARACTERS.md`](../references/fields/PLAYER_CHARACTERS.md) and [`references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`](../references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md)) — if the protagonist changes
- Tracked item initial values (see [`references/fields/TRACKED_ITEMS.md`](../references/fields/TRACKED_ITEMS.md)) — if mechanics differ; if the variant adds new tracked items, prefer `dataType: "yaml"` with a unique snake_case `variableName` over the deprecated `xml` (see [`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md))
- New or altered trigger logic (see [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md) and [`references/mechanics/PAWSCRIPT.md`](../references/mechanics/PAWSCRIPT.md)) — an `effectRunScript` effect may only reference existing tracked-item `variableName`s and must never write to `$player`/`$game`

## Step 5 — Validate and audit the variant

1. Call `validate_world(target_path)` — fix any errors.
2. Call `audit_world(target_path)` — share findings with the author.

## Step 6 — Compare with the source

Call `compare_worlds(source_path, target_path)` and then `get_diff_summary(source_path, target_path)` to produce a clear narrative of what diverged.

Present the summary to the author. This serves as documentation of what makes the variant distinct.

---

Never modify the source world. All edits go to the copy at the target path. Use `Edit` (not full `Write`) on the target so platform-managed fields survive.
