---
description: Build a new sequel world from an existing Infinite Worlds world and one or more story-export files.
argument-hint: "[source_world_path] [story_export_path...] [target_path]"
---

# Sequel World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author create a **sequel** to an existing Infinite Worlds world — building a new world file that begins where the story export left off, informed by what actually happened in play.

## Recommended reading

The references in `references/` cover the sequel-specific disciplines:

- **Before proposing any field value** → read `references/guidance/CITATION_METHODOLOGY.md`. Every `**Proposed Value:**` block must be immediately followed by a well-formed `**Evidence:**` line in one of the four accepted formats. The citation gate Stop hook enforces this automatically.
- **For no-fabrication discipline** → read `references/guidance/STORY_ACCURACY_GUARDRAILS.md`. If the story export doesn't show evidence for a field, use `NO_STORY_EVIDENCE:` — don't invent.
- **For which tool call maps to which field** → read `references/guidance/STORY_CONTEXT_DISTRIBUTION.md`. Follow the tiered loading sequence; budget 3–7 `turn_detail` queries total.
- **For tool signatures and output shapes** → read `references/mechanics/STORY_EXTRACTION_TOOL.md`.
- **For character authoring** → read `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`. Story export data can inform character updates but never licenses fabricating dossier details.

---

## Step 1 — Confirm paths

If `$ARGUMENTS` is supplied, parse it as space-separated paths: first path = source world JSON, last path = target output path, all paths in between = story export `.txt` files. If any path is missing, ask the user for it in turn.

**Resolve every path to an absolute path before passing it to any tool.** The MCP server process has a different working directory from your session. If the user gave you a relative path, join it with your session's current working directory — e.g. run `realpath -m "<path>"` (the `-m` flag resolves not-yet-created paths; or take `pwd` and prepend it manually). A leading `~` is fine; the tools expand it.

1. Call `confirm_path` on the **source world path** (absolute). It must exist.
2. Confirm each **story export path** (absolute). Each must exist (these are `.txt` files exported from IW).
3. Ask the user for the **target output path** for the sequel world (if not supplied via arguments).
4. Call `confirm_path` on the **target path**. Its parent must exist; warn if the file already exists.
5. Decide on an **extraction directory** — a directory adjacent to the target for the structured extraction output (e.g., if the target is `/path/to/sequel_world.json`, use `/path/to/extracted_story/`). Tell the user where it will be written.
6. Present all resolved paths and wait for confirmation before proceeding.

---

## Step 2 — Copy source to sequel target (via `make_draft_world`)

**Never modify the source world.** Call `make_draft_world(source_path, target_path)` with both absolute paths — pass the author's chosen `target_path` explicitly so the tool copies there (the same spinoff idiom: supplying the target overrides the `_draft` naming). The tool copies the source untouched, bumps `version`, and surfaces it first.

Then call `validate_world(target_path)` to confirm the copy is clean.

From here on, all edits target the **sequel copy** at `target_path`. The source is the diff baseline and is never touched again.

---

## Step 3 — Build the character list

Call `get_character_list(world_path=<source_path_absolute>)`.

Present the returned `character_list` to the author. Ask:
- Are there characters missing from this list (e.g., characters introduced during the story who aren't in the original world)?
- Are there aliases or short forms that appear in the story text for any character (e.g., "Daro" for "Lord Daro")?

The author may also choose to skip the character list entirely (extraction will still run; only `character_index.json` is skipped).

Wait for confirmation before proceeding to Step 4.

---

## Step 4 — Extract story data

Call `extract_story_data` with the confirmed inputs:

```
extract_story_data(
    input_paths=[<story_export_path_1>, <story_export_path_2>, ...],
    extraction_dir=<extraction_dir_absolute>,
    character_list=<confirmed_list_or_omit_if_skipped>
)
```

All paths must be absolute. If the call returns an error, present it to the author and stop — do not proceed to field proposals if extraction failed.

Share the extraction summary with the author (total turns, turn range, warnings, files written).

---

## Step 5 — Arm the citation gate

The citation gate Stop hook will verify that every field proposal you make cites its evidence source. Arm it now by running these two commands separately (do NOT chain them with `&&`):

```bash
mkdir -p "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active"
```

```bash
touch "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/${CLAUDE_CODE_SESSION_ID}"
```

The second command uses `CLAUDE_CODE_SESSION_ID` (not `CLAUDE_SESSION_ID`) — this is the environment variable that holds the current session's UUID.

If either command fails, report the error to the author before proceeding. Do not begin field proposals without the gate armed.

> The gate will also fire on session exit. If you need to exit early (error, abort, or author request), disarm the gate first — see Step 8.

---

## Step 6 — Query story data and propose fields

Load story data using the tiered sequence in `references/guidance/STORY_CONTEXT_DISTRIBUTION.md`:

**Always load first (Tier 1 — run all three):**
1. `query_story_data(extraction_dir=<dir>, category="manifest")`
2. `query_story_data(extraction_dir=<dir>, category="metadata")`
3. `query_story_data(extraction_dir=<dir>, category="turn_index")`

Then use on-demand (Tier 2–3) queries for specific fields that need deeper data.

**For each field, propose using EXACTLY this template:**

```
**Field:** <field name>
**Proposed Value:** <value>
**Evidence:** <evidence in one of the 4 formats from CITATION_METHODOLOGY.md>
```

All three lines are required for every proposal. The gate checks every `**Proposed Value:**` block for a following `**Evidence:**` line.

**Key field notes:**

- `objective` has **no story-export source** (the metadata `objective` is always null). Always cite `CARRY_FORWARD:` (same goal as original world) or `USER_DIRECTED:` (author provided new goal).
- `img_appearance` and `img_clothing` for characters are author-input only — the story export contains no image prompts. Stop and ask the author if these need to be set.
- `instructions`, `authorStyle`, `triggerEvents`, `instructionBlocks`, `loreBookEntries`, `imageStyle*` all carry forward from the source world unless the author directs otherwise.

**Approval loop (same as `modify-world`):**

1. Show the current value from the source world (or "not set").
2. Propose the new value with the evidence block.
3. Wait for the author to approve or revise.
4. `Edit` the target world in place — use `Edit` (not full `Write`) so platform-managed fields survive. Always `Read` before `Edit`.

**Validate after each batch of 3–5 related edits:**

```
validate_world(target_path)
```

Fix any errors before continuing.

---

## Step 7 — Validate, audit, and compare

Once the author has approved all proposed changes:

1. Call `validate_world(target_path)` — fix any remaining errors.
2. Call `audit_world(target_path)` — share the findings with the author.
3. Call `compare_worlds(source_path, target_path)` and `get_diff_summary(source_path, target_path)` — present a clear narrative of what changed from source to sequel.

---

## Step 8 — Disarm the citation gate

After the session concludes (whether complete, early exit, or abort), disarm the gate:

```bash
rm -f "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/${CLAUDE_CODE_SESSION_ID}"
```

This prevents the gate from firing in future sessions that don't involve a sequel-world flow. Run this command on normal completion AND on any early exit or abort — the gate must not be left armed after the session ends.

---

Never modify the source world. All edits go to the copy at the target path. Use `Edit` (not full `Write`) on the target so platform-managed fields survive.

The sequel's evidence is only as good as the story data. If the export doesn't show it, don't assert it — cite the gap.
