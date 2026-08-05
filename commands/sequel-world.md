---
description: Build a new sequel world from an existing Infinite Worlds world and one or more story-export files.
argument-hint: "[source_world_path] [story_export_path...] [target_path]"
---

# Sequel World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author create a **sequel** to an existing Infinite Worlds world — a new world file that begins where the story export left off, informed by what actually happened in play. This command carries its own citation and no-fabrication discipline inline (see "The proposal contract" below); there is no separate citation reference to load.

**Before you start, also read:**

- `references/mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md` — how to drive the `extract_story_data` / `query_story_data` / `get_character_list` tools: the tiered loading sequence and the `turn_detail` query budget (3–7 per session).
- `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md` — the no-fabrication discipline for characters.

---

## Step 1 — Confirm paths

Resolve every path to an **absolute** path before passing it to a tool — the MCP server runs in a different working directory from your session (join a relative path with `pwd`, or run `realpath -m "<path>"`; a leading `~` is fine, the tools expand it). If `$ARGUMENTS` is supplied it's space-separated: first = source world JSON, last = target output world JSON, the rest = story export `.txt` files. Only `.json` worlds and `.txt` exports are accepted — if the author offers anything else, tell them.

1. `confirm_path` the **source world JSON** (must exist).
2. `confirm_path` each **story export `.txt`** (must exist).
3. Ask for the **target output path** if not supplied, then `confirm_path` it — its parent must exist; warn if the file already exists.
4. Choose an **extraction directory** adjacent to the target (e.g. target `/path/sequel.json` → `/path/extracted_story/`); tell the author where it will be written.
5. Present all resolved paths and wait for confirmation before proceeding.

---

## Step 2 — Copy source to sequel target (via `make_draft_world`)

**Never modify the source world.** Call `make_draft_world(source_path, target_path)` with both confirmed absolute paths — pass the author's chosen `target_path` explicitly so the tool copies there (the same spinoff idiom: supplying the target overrides the `_draft` naming). The tool copies the source untouched, bumps `version`, and surfaces it first.

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
> **Field:** `<field name>`
> **Proposed Value:** `<value>`
> **Evidence:** `<where it came from>`
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

The second command uses `CLAUDE_CODE_SESSION_ID` (not `CLAUDE_SESSION_ID`) — the environment variable that holds the current session's UUID. If either command fails, report the error to the author and ask them what they'd like to do before proceeding.

**If the author says no**, continue without arming. Still follow the proposal contract below by hand — the gate simply won't enforce it.

**Turning it off later.** If the author asks to turn the gate off at any point, disarm it immediately — see Step 7. You can re-arm it the same way if they change their mind.

> The gate mechanism is flow-agnostic (it keys on the per-session marker file, not on "sequel"). This command is the only one that arms it today; if another command ever needs the same evidence discipline, lift the proposal contract below into a shared reference at that point.

---

## The proposal contract (read before Step 6)

Whenever you propose a field value in this flow, follow one discipline: **propose a value, cite where it came from, never invent.** The citation gate enforces the shape of this when armed; the discipline applies even when it isn't.

### The proposal template

Propose each field value as this exact block:

```
**Field:** <field name>
**Proposed Value:** <value>
**Evidence:** <one of the four formats below>
```

All three lines are required. Keep `**Field:**` and `**Proposed Value:**` on consecutive lines with **no blank line between them** — a blank line there breaks the gate's structural match and the proposal is treated as uncited and blocked. The `**Evidence:**` line may follow after the value; only it is inspected for content. Evidence is shown in chat only — it is **never** written to the world JSON.

### The four evidence formats

1. **Story citation** — supported by extracted story data. The gate validates the prefix `From Turn #<N>` or `From Story Metadata`; the suffix is a readability convention you should still use:
   - `From Turn #<N> Outcome: <quote or paraphrase>`
   - `From Turn #<N> Secret Info: <…>`
   - `From Turn #<N> Tracked Item <name>: <value>`
   - `From Story Metadata: field <field name>` (e.g. the title, story background, or character name/skills/background)

   Cite only turns you have actually queried (verify via `turn_index`).
2. **`USER_DIRECTED: <what the author said>`** — the author gave a direct instruction this session.
3. **`CARRY_FORWARD: <why it's unchanged>`** — the value comes from the **original world JSON** and no story event changed it. This is how *every* static field the export doesn't touch is sourced (`objective`, `authorStyle`, image style, an unaddressed NPC's `detail`, …).
4. **`NO_STORY_EVIDENCE: <what you looked for and didn't find>`** — you checked the export, found nothing, and are not carrying a value forward. Prefer this honest gap over silence or invention.

Each prefix must be followed by real text — an empty `CARRY_FORWARD:` / `USER_DIRECTED:` / `NO_STORY_EVIDENCE:` is rejected, as is any line with no recognized prefix (`Based on context`, `From the story`, `I inferred this`).

### One field per message — except complex entities

Propose **one field per message** by default: one block, then wait for approval. The exception is multi-sub-field entities, which you propose in small **ordered batches** (one message, several blocks — each block still needs its own `**Evidence:**` line; approve each batch before the next). Field names below are the schema's; the IW editor's labels differ slightly ("Brief Summary" = `one_liner`, "Full List of Names" = `names`).

- **Tracked item** (`trackedItems[*]`): (1) `name`, `dataType`, `visibility`; (2) `description`, `autoUpdate`, `updateInstructions` (only meaningful when `autoUpdate` is true); (3) `initialValue`, `initialValueBasedOnPC`. Beyond the structural fields below (`id`, `positionInList`), the schema also requires `autoUpdate` — don't let it slip through batch (2) unset, or `validate_world` rejects the item.
- **Keyword Instruction Block** (`loreBookEntries[*]`): `name`, `keywords`, `content` — one message.
- **Extra Instruction Block** (`instructionBlocks[*]`): `name`, `content` — one message.
- **Player character** (`possibleCharacters[*]`): (1) `name`, `description`, `skills`; (2) `portraitPromptDetails`, `initialTrackedItemValues`.
- **NPC** (`NPCs[*]`): (1) `name`, `names`, `location`, `one_liner`; (2) `detail`, `secret_info`; (3) `appearance` plus the portrait prompts `img_appearance` / `img_clothing`.
- **Trigger event** (`triggerEvents[*]`): (1) `name`, `triggerConditions` (may be empty for a start-of-game / always-fire trigger — only `triggerEffects` is schema-required); (2) `triggerEffects`.

> **Structural fields (set mechanically, not cited).** Every *new* entity also needs an `id` — mint it with `mint_ids`, never hand-write — and a `positionInList` (its ordinal index in its list). The schema requires these, but they aren't evidence-backed values, so set them when you create the entity rather than proposing them; carried-forward entities already have both. For the complete required-field set of any entity, see `references/WORLD_JSON_SCHEMA_v2.2.md` or `references/world_v2.2.schema.json`.

Worked example — one NPC batch-1 message:

```
**Field:** NPC "Mira" — name
**Proposed Value:** Mira
**Evidence:** CARRY_FORWARD: Same NPC as the source world.

**Field:** NPC "Mira" — names (aliases)
**Proposed Value:** ["Mira", "the Courier"]
**Evidence:** From Turn #8 Outcome: A guard addressed her as "the Courier".

**Field:** NPC "Mira" — location
**Proposed Value:** The river docks
**Evidence:** From Turn #14 Outcome: Mira was last seen leaving the river docks.

**Field:** NPC "Mira" — one_liner
**Proposed Value:** A courier who now runs the dock smugglers.
**Evidence:** From Turn #14 Secret Info: Mira had taken over the smuggling ring.
```

### No-fabrication discipline

The story export is the evidence floor. Valid sources, strongest first: (1) the author's direct statement this session; (2) extracted story data (turn outcomes, secret info, tracked-item states, metadata); (3) the original world JSON (carry-forward). **Never** acceptable: your sense of what "probably" happened between beats, genre/sequel tropes, inferences from a name or role, or training-data narrative conventions.

- **Query before proposing, not after.** Pull the relevant extract data, see what it shows, then propose — don't draft from intuition and backfill a citation.
- **Empty or unchanged stays so.** If the export doesn't show a field changing, carry the original world's value (`CARRY_FORWARD:`); don't synthesize a "likely" sequel state. (Especially tracked-item labels/instructions, NPC `detail`/`secret_info`, factions, relationship and arc states.)
- **Don't invent events or resolve what the story left open.** A cliffhanger or unresolved arc is inherited as-is — flag it unresolved in `detail`, don't paper over it.
- **No evidence → say so.** Use `NO_STORY_EVIDENCE:` and name what you checked; let the author decide.
- **Characters:** follow `CHARACTER_AUTHORING_GUARDRAILS.md`. A character appearing in a turn does not license rewriting their dossier — only the explicitly revealed content updates it.

---

## Step 6 — Query story data, then propose fields

Load the story data following `references/mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md` (Tier-1 first, then Tier-2/3 on demand within the 3–7 `turn_detail` budget), then propose each field per the proposal contract above. **This is a sequel — let the world evolve;** don't reflexively carry fields forward. Use the sourcing rules below.

### Sourcing rules (per field)

| Field | Where the value comes from |
|---|---|
| `title` | `metadata.title` (often the original title; may want a sequel suffix). |
| `description` | `metadata.storyBackground`. |
| `background` | `metadata.storyBackground` blended with how the story ended (relevant turn outcomes). |
| `instructions` | **Usually rewrite.** The export has no instruction text, but the sequel's runtime instructions must reflect where the story now stands (events that happened, the new starting situation, changed stakes). Treat the original as a draft to revise, not a value to copy. |
| `firstInput` | The last turn's outcome (`turn_detail`, `turns=["last"]`) and/or author direction — the sequel's opening premise. |
| `objective` | The **original world JSON** (`CARRY_FORWARD:`), exactly like any other static field — or `USER_DIRECTED:` if the author sets a new goal. (The export has no Objective section, so the extract's `metadata.objective` is always null; read `objective` from the source world, not the extract.) |
| `possibleCharacters[*].name` | `metadata.character.name`. |
| `possibleCharacters[*].skills` | `metadata.character.skills` — but it's a raw string; parse it and map onto the world's existing `skills` object, don't copy verbatim. |
| `possibleCharacters[*].description`, `portraitPromptDetails` | Original world; for portrait details, carry forward if present, else synthesize from any story-narrated PC appearance, else ask. |
| `trackedItems[*]` (final values) | `tracked_state` last snapshot (`toTurn == manifest.totalTurns`). Labels/structure carry forward from the original. |
| `NPCs[*].detail`, `secret_info` | `character_index` + `turn_detail`; update only what the export revealed, carry forward the rest. |
| `NPCs[*].appearance`, `img_appearance`, `img_clothing` | Carry forward if the source world has them; else **synthesize from story-narrated appearance** (cite the turn — re-expressing a described look is grounding, not fabrication); else ask. `appearance` is narrative prose; `img_*` are portrait prompts it can seed. |
| `triggerEvents`, `instructionBlocks` (EIBs), `loreBookEntries` (KIBs) | Revisit against the story — disable/rewrite what the story resolved or made stale, add what the sequel needs, carry forward the rest. |
| `authorStyle`, `imageStyle*` / `illustrationStyle*` | **True carry-forwards** — the export has no equivalent and writing/visual style doesn't change between games. |

### Approval loop

1. Show the current value from the source world (or "not set").
2. Propose the new value with its evidence block.
3. Wait for the author to approve or revise.
4. If the author asks you to revise anything at all, return to step 1. If they approve, move to step 5.
5. `Edit` the target world in place — use `Edit` (not full `Write`) so platform-managed fields survive. Always `Read` before `Edit`.

Validate after each batch of 3–5 related edits with `validate_world(target_path)`; fix errors before continuing.

---

## Step 7 — Disarm the gate, then validate, audit, and compare

The field-by-field pass is over, so **disarm the citation gate first** — otherwise it keeps inspecting every remaining response (validation summaries, the diff narrative) for a proposal template they won't have. Also disarm immediately if the author asks to turn it off mid-flow, or on any early exit/abort; `rm -f` is safe even if the gate was never armed.

```bash
rm -f "${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/${CLAUDE_CODE_SESSION_ID}"
```

Then, once the author has approved all changes:

1. `validate_world(target_path)` — fix any remaining errors.
2. `audit_world(target_path)` — share the findings with the author.
3. `compare_worlds(source_path, target_path)` and `get_diff_summary(source_path, target_path)` — present a clear narrative of what changed from source to sequel.

---

The sequel's evidence is only as good as the story data. If the export doesn't show it, don't assert it — carry it forward from the source world or cite the gap.
