---
name: spinoff-world
description: Derive a variant world from an existing Infinite Worlds world. Activated by phrases like "create a variant world", "spin off a world", "make a variant of my world", "create an alternative version of", "base a new world on", or "fork my world".
version: 0.1.0
---

# Spinoff World Workflow

You are helping an author create a **variant** of an existing Infinite Worlds world — keeping the original intact and producing a new divergent version.

## Step 1 — Confirm paths

1. Call `confirm_path` on the **source** world path. It must exist.
2. Ask the user for the **target** output path for the variant.
3. Call `confirm_path` on the target path. Its parent must exist; warn if the file already exists.
4. Present both resolved paths and wait for confirmation before proceeding.

## Step 2 — Copy the source

Use the Bash tool or `Read` + `Write` to copy the source world JSON to the target path:

```python
# Pseudo-code for the copy step
target.write_text(source.read_text())
```

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

Key fields that usually diverge in a spinoff:
- `title`, `description`, `background` — identify the variant clearly
- `designNotes` — record why this variant exists (not sent to AI)
- Character `name` and `description` if the protagonist changes
- Tracked item initial values if mechanics differ

## Step 5 — Validate and audit the variant

1. Call `validate_world(target_path)` — fix any errors.
2. Call `audit_world(target_path)` — share findings with the author.

## Step 6 — Compare with the source

Call `compare_worlds(source_path, target_path)` and then `get_diff_summary(source_path, target_path)` to produce a clear narrative of what diverged.

Present the summary to the author. This serves as documentation of what makes the variant distinct.

---

**Reminder**: The source world must never be modified. All edits go to the copy at the target path. Always use `Edit` on the target file to preserve platform-managed fields.
