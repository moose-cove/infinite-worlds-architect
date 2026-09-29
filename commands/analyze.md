---
description: Read-only Q&A analysis of an existing Infinite Worlds world.
argument-hint: "[world_path]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(realpath *)
  - Bash(pwd)
  - Bash(wc *)
  - WebFetch(domain:infiniteworlds.mywikis.wiki)
  - WebFetch(domain:infiniteworlds.app)
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__confirm_path
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__validate_world
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__audit_world
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__read_world_field
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__format_world_for_review
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__get_schema_summary
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__compare_worlds
  - mcp__plugin_infinite-worlds-architect_iw-json-tools__get_diff_summary
---

<!--
Usage: /infinite-worlds-architect:analyze [world_path]
  world_path is optional — the command asks for it if omitted.
Requires: the iw-json-tools MCP server (bundled with this plugin).

NAMING DECISION: `analyze` rather than the siblings' verb-noun `analyze-world` — chosen
deliberately by the plugin author; the plugin namespace prevents any collision.

ALLOWED-TOOLS: pre-approves the read-only tools the body calls so they run without a
permission prompt. It does NOT restrict anything — per the Claude Code docs, unlisted tools
(Edit, Write, make_draft_world, mint_ids) stay callable under the user's normal permission
settings, and the grant lasts only for the invoking turn. The read-only contract is the
prose below. Keep the list to read-only tools the body actually uses; WebFetch is scoped to
the two IW domains the agent guide cites so untrusted world text cannot steer an
unprompted fetch elsewhere.
-->

# Analyze World

@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md

You are helping an author **understand** an existing Infinite Worlds world JSON. This command is
**read-only**: you load the world, then answer whatever the author wants to know about it —
how it works, why something behaves the way it does, what is weak or missing, how two parts
interact. You never edit the world. If the author asks for a change, point them to
`/infinite-worlds-architect:modify-world` and offer to explain what the change would involve.

## Recommended reading

Load references on demand, matched to the question being asked — not all up front:

- **"Why does / doesn't this trigger fire?"**, effect ordering, PawScript conditions → `references/fields/TRIGGER_EVENTS.md`, `references/mechanics/AI_RUNTIME_MECHANICS.md`, and `references/mechanics/PAWSCRIPT.md` if any `effectRunScript` or `triggerOnPawScript` is involved.
- **"What does the AI actually see each turn?"**, token budget, instruction precedence → `references/mechanics/AI_RUNTIME_MECHANICS.md` and `references/fields/MAIN_INSTRUCTIONS.md`.
- **"Is this content in the right field?"**, redundancy, bloat → `references/guidance/FIELD_ALLOCATION_STRATEGY.md`.
- **Characters and NPCs** — consistency, what the AI knows about whom → `references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md`, `references/guidance/LAYERED_KNOWLEDGE_ISOLATION.md`, `references/fields/OTHER_CHARACTERS.md`, `references/fields/PLAYER_CHARACTERS.md`.
- **Tracked items** — what is tracked, how values flow, YAML shape → `references/fields/TRACKED_ITEMS.md` and `references/fields/YAML_TRACKED_ITEMS.md`.
- **Lore and keyword blocks** — when they surface, the awareness paradox → `references/fields/KEYWORD_INSTRUCTION_BLOCKS.md`.
- **Endings** — victory/defeat paths, `effectEndsGame` semantics → `references/fields/VICTORY_DEFEAT.md`.
- **Import/export quirks** — "will IW keep this on import?" → `references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`.
- **Any other field** → the matching file in `references/fields/`. When unsure where something lives, start from `references/README.md`; for exact field shapes and enums, `references/WORLD_JSON_SCHEMA_v2.4.md` or `get_schema_summary()`; for "is this a known design pattern?", `references/patterns/`.

## Step 1 — Confirm the world path

If `$ARGUMENTS` is non-empty, use it as the world path. Otherwise, ask the user for the path.

**Resolve the path to an absolute path before passing it to any MCP world tool** (`confirm_path`, `validate_world`, `read_world_field`, `audit_world`, …). These tools run in a separate MCP server process whose working directory is *not* your session's, so they reject relative paths. If the user gave you a relative path, join it with your session's current working directory first — e.g. run `realpath -m "<path>"`, or prepend `pwd`. A leading `~` is fine; the tools expand it.

Call `confirm_path(path)` with that absolute path. Present the resolved path and confirm the file exists before proceeding.

## Step 2 — Load the world into context

This command works on the **source file directly** — do **not** call `make_draft_world`. The draft-copy guard in the agent guide exists to protect a world that is about to be *edited*; nothing here edits, so a draft would only be noise. The corollary: **never call `Edit` or `Write` on the world path during this command.**

1. Call `Read` on the world JSON to load the whole world into context. Analysis questions routinely span entities (a trigger's condition points at a tracked item that an NPC's instructions reference), so you want the full picture available rather than field-by-field peeks. Check the size first with `wc -lc`. A single `Read` returns at most ~2000 lines and refuses files over its token limit, so if the world is longer than that, or `Read` truncates or errors, read it in `offset`/`limit` chunks until you reach the last line — a silently truncated load makes every cross-reference trace wrong. For a very large world (roughly above 400 KB), load `format_world_for_review(path)` instead and rely on `read_world_field` / `Grep` for the detail — and tell the author you are in that mode, since cross-reference tracing is then only as complete as what you chose to pull.

   Also establish whether the file is the author's **source** or an **IW export** (ask if it is not obvious). It changes how some findings read: in an export, a gate IW deleted on import is already gone, so a trigger with `"triggerConditions": []` may be what is left of a deleted condition; and an export under-reports what IW is still evaluating (a blank `triggerOnPawScript` `data` disappears from the export but keeps erroring every turn — see `references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`).
2. Call `validate_world(path)`. Report errors and warnings briefly — they are often the answer to a question the author is about to ask, and any analysis you give must be caveated by known invalidity.
3. Call `audit_world(path)`. Keep its findings in mind; surface them when they bear on a question, not as a wall of text up front.
4. Give the author a **short orientation** (5–10 lines): title and premise in a sentence, schema version, counts of player characters / NPCs / tracked items / triggers / declared events (top-level `conditions`) / instruction blocks / lore entries, whether `victoryCondition` and `defeatCondition` are set, and the one or two validator or audit findings most worth knowing about. Do not narrate the whole world — that is what the author's questions are for.

## Step 3 — Ask what the author wants to know

Ask: "What would you like to know about this world?"

Offer a few example directions only if the author seems unsure, e.g.:

- Walk me through how the game can end.
- Why doesn't trigger X fire when Y happens?
- Which NPC knows about Z, and how does the AI learn that?
- Where is this world spending its token budget?
- What is redundant, contradictory, or missing?
- Trace what happens on the turn the player does W.

## Step 4 — Analyze deeply, answer precisely

For each question, do the work before answering — do not answer from a skim of the JSON.

1. **Locate the evidence.** Pull the exact entities involved: quote the relevant trigger, tracked item, instruction block, or character field. Use `read_world_field` for a precise re-read of a single field when the loaded JSON is long; use `Grep` on the file for "where is this ID / variableName / keyword referenced?" questions; use `get_schema_summary()` for "what does this field actually do / accept?" questions; use `compare_worlds` / `get_diff_summary` when the author has a second version to compare against ("it worked in the old copy"). Questions about a specific playthrough ("why didn't X fire on turn 12?") are answered by IW's World Debug panel or the story-export tools, not by this command — say so. Offer `format_world_for_review(path)` only when the author wants a rendered overview rather than a targeted answer.
2. **Trace the mechanics, don't guess them.** For anything involving runtime behavior — trigger firing, effect order, tracked-item updates, what the AI sees — load the matching reference from the list above and reason from what it actually says. Where the references are silent, say so and mark the answer as inferred, not confirmed. Apply the wiki discipline from the agent guide: the wiki is last resort and is cited with explicit skepticism.

   For **"why doesn't trigger X fire?"** check the known trigger-killers first. They split by how they fail:
   - **Deleted on import — no trace anywhere.** A pre-v2.4 bare-array `triggerPrereqs` / `triggerBlockers` (`references/fields/TRIGGER_EVENTS.md`), or a `triggerOnTrackedItem` with an absent or empty `textComparison` (`references/WORLD_JSON_SCHEMA_v2.4.md`, `references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`). IW drops the condition, leaving the trigger under-gated (other conditions remain) or dead (it was the only one).
   - **Never fires, no error.** A trigger with no conditions at all (only `triggerOnStartOfGame: true` is exempt).
   - **Kept on import, fails every turn — logged in World Debug.** A comparison inside a `triggerOnRandomChance` formula (`"($x > 2) * 100"`); and the malformed `triggerOnPawScript` shapes in `references/mechanics/PAWSCRIPT.md` — blank `data` (an absent `data` key is worse: it does nothing and logs nothing), a bare `$handle` with no comparison (it works out to a value, not true/false), `<<name>>` interpolation used as a bare operand (substituted before parsing, so `<<flavor>> = "Lemon"` becomes `Lemon = "Lemon"` and errors), an undeclared `$name`, or a YAML path that does not exist.
   - **Fired once, did nothing, now spent.** A one-shot trigger whose `effectRunScript` errored: the script rolls back, but the trigger still counts as fired — it never runs again, and downstream `triggerPrereqs` on it still advance (`references/mechanics/PAWSCRIPT.md`, "Rollback is not a retry").

   For the runtime-failing kinds, suggest the author turn on World Debug's PawScript panel — it names each failure, and is the fastest way to tell a deleted condition from a surviving-but-broken one. Do not treat `validate_world` as exhaustive: it errors on some of these and only warns on others, and it is **silent** on a comparison inside a `triggerOnRandomChance` formula and on missing YAML paths — catch those by reading the trigger. A `triggerOnEvent` string missing from the top-level `conditions` registry is a registry desync (validator warning) that costs editor selectability; whether it also affects runtime matching is unverified (`probes/README.md`), so report it as a risk, not the cause.
3. **Follow every cross-reference.** A trigger condition names a tracked item — read that item's `updateInstructions` and initial value. (A `trackedItemID` of the form `skill_<name>` is a synthetic skill reference, not a dangling ID — see `references/WORLD_JSON_SCHEMA_v2.4.md`; and a per-character `initialPCValue` array is a pick-one menu, so a `contains` comparison against it is not vacuously true — see `references/fields/TRIGGER_EVENTS.md`.) For every `$name` in an `effectRunScript` body, a `triggerOnPawScript` expression, or a `triggerOnRandomChance` formula, the **root** — the text before the first `.` — must be a tracked item's `variableName`, a PawScript native (`$player`, `$game`), or, inside a script, a local bound by `for each` or `set` (`references/mechanics/PAWSCRIPT.md`). A native or a local is not a bug. A dangling root kills a `triggerOnPawScript` / `triggerOnRandomChance` gate; in a script it rolls the writes back while the trigger still counts as fired. The dot-path tail (`.leader.stats.hp` in `$party.leader.stats.hp`) is a runtime lookup that cannot be checked statically — a missing sub-path fails only in play. A `triggerPrereqs` / `triggerBlockers` names trigger IDs — find each anchor, check what fires *it*, and read `firedThisTurn`: `false` means "ever fired" (a permanent gate), `true` means a same-turn interlock. A `true` interlock is only confirmed with the anchor *earlier* in the `triggerEvents` list — a consumer above its anchor is untested, so flag it as a risk rather than a certain failure — and a one-shot anchor gives it exactly one chance (`references/fields/TRIGGER_EVENTS.md`). A keyword block matches its keywords in the **player's recent input** (fires that turn) and the **AI's recent output** (fires the following turn) — not in static fields — so ask two things: can the topic plausibly surface in play, and does anything the AI sees every turn (`instructions`, an instruction block, an NPC field) give the keyword an entry point? A block whose keyword the AI has no reason to write is the awareness paradox (see `references/fields/KEYWORD_INSTRUCTION_BLOCKS.md`). Matching is case-insensitive **substring** matching, so also check every keyword for accidental hits (`"art"` matches *part*, *start*, *heart*) — and a triggered block stays injected for three turns, so a flooding block is the answer to many "where is the token budget going?" questions. An analysis that stops at the first hop is usually wrong.
4. **Consider the turn lifecycle.** For "what happens when…" questions, walk the turn in the order `references/mechanics/AI_RUNTIME_MECHANICS.md` gives and say at which step each relevant piece acts. The documented ordering consequence to look for: the AI writes turn N's narrative *before* tracked-item updates, trigger evaluation, and effects land, so nothing that changes state on turn N can show up in turn N's prose — the earliest the AI can react is turn N+1. Per the documented lifecycle, AI-driven tracked-item updates are written before any trigger condition reads them, so a condition should never see a stale AI update. Triggers run in list order, which creates two intra-pass ordering traps: an `effectRunScript` write is visible only to triggers *later* in `triggerEvents` — a `triggerOnPawScript` consumer placed before its producer reads last turn's value — and a `firedThisTurn: true` prereq wants its anchor earlier in the list (Step 4.3). See `references/fields/TRIGGER_EVENTS.md`, "Evaluation order matters".
5. **Answer in IW terms, with citations.** Lead with the answer in one or two sentences. Then give the evidence chain: which entity (by `id` and name), which field, which reference or validator/audit output supports the conclusion. Quote fields verbatim when the wording is the point (a `textComparison`, a PawScript expression, a keyword). For "is this good?" questions, cite the specific guidance principle being applied rather than asserting taste.
6. **Distinguish fact from judgment.** "This trigger cannot fire because its condition references a `variableName` that does not exist" is fact. "This world leans too hard on `instructions` for lore" is judgment grounded in `references/guidance/FIELD_ALLOCATION_STRATEGY.md`. Label them so the author knows which is which.

For broad questions ("what's wrong with this world?", "how does the whole thing hang together?"), structure the answer around the world's own systems — endings, progression, characters, tracked state, lore — rather than around the JSON's key order, and lead with the findings that would most change what the author does next.

## Step 5 — Keep going

After each answer, ask whether the author has another question. Stay in analysis mode for the whole session: **no edits, no draft copy, no `mint_ids`**. If the author decides they want to change something, summarize what the change would involve (which entities, which fields, which references to consult) and hand off to `/infinite-worlds-architect:modify-world`.

---

This command never modifies the world file. All `Edit`/`Write` activity on the world path is out of scope here — use `/infinite-worlds-architect:modify-world` for changes.
