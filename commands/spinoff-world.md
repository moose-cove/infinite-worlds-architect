---
description: Derive a variant world from an existing Infinite Worlds world, keeping the original intact.
argument-hint: "[source_path] [target_path]"
---

# Spinoff World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author create a **variant** of an existing Infinite Worlds world — keeping the original intact and producing a new divergent version.

## Recommended reading

The references in `references/` cover authoring judgments specific to spinoffs:

- **Before changing any character** → read `references/CHARACTER_AUTHORING_GUARDRAILS.md`. Spinoffs especially benefit from the no-fabrication rule because the temptation is to "complete" thinly-sketched source characters by inventing detail. The source dossier is the floor, not a starting point to embellish. Premise changes don't license character changes — ask the author what carries forward and what doesn't.
- **When deciding whether to keep or restructure source content** → read `references/FIELD_ALLOCATION_STRATEGY.md`. A spinoff with a different premise often needs content reallocated (e.g., the original's `background` describes the wrong setting; some of its `instructionBlocks` become irrelevant). Use the allocation rules to decide what to keep, what to move, and what to drop.
- **When changing `instructions`, `authorStyle`, or any trigger that the spinoff inherits** → read `references/AI_RUNTIME_MECHANICS.md` to understand what those fields actually shape at runtime.
- **For per-field judgment calls** → read the matching file in `references/sections/`.

## Step 1 — Confirm paths

If `$ARGUMENTS` contains two paths (source then target, space-separated), use them directly. Otherwise, ask the user for each path in turn.

1. Call `confirm_path` on the **source** world path. It must exist.
2. Ask the user for the **target** output path for the variant (if not supplied via arguments).
3. Call `confirm_path` on the target path. Its parent must exist; warn if the file already exists.
4. Present both resolved paths and wait for confirmation before proceeding.

## Step 2 — Copy the source (with a copy command, never Read + Write)

**Never modify the source world.** Duplicate it to the target path with a shell **copy** command — do **not** read the whole file into context and write it back out:

```
cp "<source_path>" "<target_path>"
```

A real `cp` is a byte-for-byte duplicate: it preserves key order, formatting, and any unknown platform-managed fields exactly, and costs no tokens. (`cp` takes no JSON *content* on the command line, so the heredoc-escaping hazard that otherwise bans Bash for JSON surgery does not apply here — the ban is on shell heredocs and inline scripts that manipulate JSON *content*, not on a plain file copy.)

Then:

1. **Bump the `version` attribute on the copy.** Read the target's `version` string (e.g. `"1.04"`) and `Edit` it to increment the trailing component by 1 (`"1.04"` → `"1.05"`), preserving any zero-padding. Skip if the world has no `version` field.
2. Call `validate_world(target_path)` to confirm the copy is clean.

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

Key fields that usually diverge in a spinoff (read the matching section file in `references/sections/` before drafting changes):
- `title`, `description`, `background` (see [`references/sections/INTRODUCING_THE_STORY.md`](../references/sections/INTRODUCING_THE_STORY.md)) — identify the variant clearly
- `designNotes` (see [`references/sections/MAIN_INSTRUCTIONS.md`](../references/sections/MAIN_INSTRUCTIONS.md)) — record why this variant exists (not sent to AI)
- Character `name` and `description` (see [`references/sections/PLAYER_CHARACTERS.md`](../references/sections/PLAYER_CHARACTERS.md) and [`references/CHARACTER_AUTHORING_GUARDRAILS.md`](../references/CHARACTER_AUTHORING_GUARDRAILS.md)) — if the protagonist changes
- Tracked item initial values (see [`references/sections/TRACKED_ITEMS.md`](../references/sections/TRACKED_ITEMS.md)) — if mechanics differ

## Step 5 — Validate and audit the variant

1. Call `validate_world(target_path)` — fix any errors.
2. Call `audit_world(target_path)` — share findings with the author.

## Step 6 — Compare with the source

Call `compare_worlds(source_path, target_path)` and then `get_diff_summary(source_path, target_path)` to produce a clear narrative of what diverged.

Present the summary to the author. This serves as documentation of what makes the variant distinct.

---

Never modify the source world. All edits go to the copy at the target path. Use `Edit` (not full `Write`) on the target so platform-managed fields survive.
