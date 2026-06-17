---
description: Build a new sequel world from an existing Infinite Worlds world and one or more story-export files.
argument-hint: "[source_world_path] [story_export_path...] [target_path]"
---

# Sequel World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author create a **sequel** to an existing Infinite Worlds world — building a new world file that begins where the story export left off, informed by what actually happened in play.

## Required reading

Read **all four** of these references before proposing any field value — they are not optional, and each governs a discipline this workflow depends on.

(The story-extraction MCP tools themselves — `extract_story_data`, `query_story_data`, `get_character_list` — are self-describing: call them and read their tool descriptions directly; there is no separate tool reference to load.)

- **Citation discipline** → `references/guidance/CITATION_METHODOLOGY.md`. The mandated proposal template, the four accepted evidence formats, and the batching rules for complex multi-field entities (NPCs, tracked items, triggers, instruction blocks). The citation gate Stop hook enforces the template whenever it is armed.
- **No-fabrication discipline** → `references/guidance/STORY_ACCURACY_GUARDRAILS.md`. If the story export doesn't show evidence for a field, cite the gap (`NO_STORY_EVIDENCE:`) — don't invent.
- **Field-to-source mapping** → `references/guidance/STORY_CONTEXT_DISTRIBUTION.md`. Which extracted data informs which world field, the tiered loading sequence, and the `turn_detail` query budget (3–7 total).
- **Character authoring** → `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`. Story data can inform character updates, but only to the extent the export explicitly shows it.

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

Present the returned `character_list` to the author as a short table so they can see exactly what was found and how aliases will be matched against the story text, e.g.:

| Character | Aliases (matched in story text) |
|---|---|
| Kira | — |
| Lord Daro | Daro, the Lord |

Then use the **`AskUserQuestion`** tool to get the author's decision — don't ask in free prose. Structure it as:

- **Question:** "Here are the characters I found in the source world. How should I handle character indexing for the story export?"
- **Header:** "Characters"
- **Options:**
  - **"Use this list as-is"** — index the export against exactly these names and aliases.
  - **"Add characters or aliases"** — there are characters introduced during the story, or short forms (e.g., "Daro" for "Lord Daro"), missing from the list. If the author picks this, follow up to collect exactly which names and aliases to add.
  - **"Skip character indexing"** — extraction still runs; only `character_index.json` is skipped.

If the author adds characters or aliases, confirm the final list back to them before continuing. Wait for the decision before proceeding to Step 4.

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

## Step 5 — Offer to arm the citation gate

Before you start proposing field values, **offer** to turn on the citation gate — don't arm it silently. The gate is a Stop hook that inspects any response containing a `**Proposed Value:**` block and blocks it unless every proposed value carries a well-formed `**Evidence:**` line. (Ordinary responses — questions, summaries, side discussions with no proposal block — pass through untouched, but turning the gate on is the natural signal that you're entering field-by-field mode.)

Explain it to the author and ask, e.g.:

> "I'm about to go field-by-field through the sequel world with you. This is a good time to turn on the **Citation Gate** — while it's on, every value I propose comes in this format:
>
> ```
> **Field:** <field name>
> **Proposed Value:** <value>
> **Evidence:** <where it came from>
> ```
>
> That keeps every proposal grounded in the story export, the original world, or your explicit direction — never invented. You can tell me to turn it off at any time. Want me to turn it on now?"

Use the **`AskUserQuestion`** tool for the decision:

- **Question:** "Turn on the Citation Gate for the field-by-field pass?"
- **Header:** "Citations" *(keep the header ≤ 12 characters — "Citation Gate" is too long for the chip label)*
- **Options:** **"Turn it on"** / **"Leave it off"**

**If the author says yes**, arm it by running these two commands separately (do NOT chain them with `&&`):

```bash
mkdir -p "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active"
```

```bash
touch "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/${CLAUDE_CODE_SESSION_ID}"
```

The second command uses `CLAUDE_CODE_SESSION_ID` (not `CLAUDE_SESSION_ID`) — the environment variable that holds the current session's UUID. If either command fails, report the error to the author before proceeding.

**If the author says no**, continue without arming. Still follow the proposal template and citation discipline by hand — the gate simply won't enforce it.

**Turning it off later.** If the author asks to turn the gate off at any point (or once the field-by-field pass is done), disarm it immediately — see Step 8. You can re-arm it the same way if they change their mind.

---

## Step 6 — Query story data and propose fields

Follow the **tiered loading sequence in `references/guidance/STORY_CONTEXT_DISTRIBUTION.md`** — start with the three Tier-1 queries (`manifest`, `metadata`, `turn_index`), then pull Tier-2/Tier-3 data on demand. That document also carries the full field-to-source mapping; consult it per field rather than guessing which query feeds which value.

**For each field, propose using EXACTLY this template:**

```
**Field:** <field name>
**Proposed Value:** <value>
**Evidence:** <evidence in one of the 4 formats from CITATION_METHODOLOGY.md>
```

All three lines are required for every proposal. The default is **one field per message**. The exception is complex entities with several sub-fields — NPCs, tracked items, trigger events, and instruction blocks — which you propose in the small, ordered batches defined in `CITATION_METHODOLOGY.md` ("How many fields per message — and complex-field batching"). When the gate is armed it checks **every** `**Proposed Value:**` block in a message, so each batched sub-field still needs its own `**Evidence:**` line.

**This is a sequel — let the world evolve.** Don't reflexively carry every field forward; the whole point is to reflect what happened in play. In particular, `instructions` usually needs to be **rewritten** to account for where the story now stands, and triggers, lore, and instruction blocks often need story-informed updates too. Carry a value forward (`CARRY_FORWARD:`) only when the story genuinely didn't change it. The field-to-source mapping in `STORY_CONTEXT_DISTRIBUTION.md` marks which fields are true carry-forwards (e.g. `authorStyle`, image/illustration style) versus which should be revisited against the story.

**Approval loop:**

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

If you armed the gate in Step 5, disarm it when the field-by-field pass is done — and **immediately** if the author asks you to turn it off mid-flow, or on any early exit or abort:

```bash
rm -f "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/${CLAUDE_CODE_SESSION_ID}"
```

`rm -f` is safe to run even if the gate was never armed. Leaving the marker in place keeps the gate nagging for the proposal template on later turns of this session, so don't skip it. (If the author later wants the gate back on, re-arm it with the Step 5 commands.)

---

Never modify the source world. All edits go to the copy at the target path. Use `Edit` (not full `Write`) on the target so platform-managed fields survive.

The sequel's evidence is only as good as the story data. If the export doesn't show it, don't assert it — cite the gap.
