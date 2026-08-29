# AI Runtime Mechanics

This document explains what happens *at play time* when a player takes a turn in an Infinite Worlds story. The schema doc (`WORLD_JSON_SCHEMA_v2.4.md`) tells you what fields a world has and what shape they take. This doc tells you what the Storyteller AI actually does with them — what it produces each turn, how variables resolve, how skill checks are evaluated.

Read this before designing `instructions`, `authorStyle`, `descriptionRequest`, `evaluationRequest`, or any trigger effect that shapes AI output. If you don't understand what the AI emits, you can't usefully constrain it.

> **Documentation status.** Infinite Worlds evolves over time, and specific
> platform behaviors may shift between releases. This document describes the
> *expected* behavior as of v2.4. If observed behavior contradicts what's
> documented here, flag the discrepancy to the user rather than silently
> working around it — surfacing drift is how the docs stay correct.

---

## 1. Instruction syntax

### Template variables — `<<name>>`

Any text field in the world JSON (and most trigger-effect string fields) supports `<<variable>>` interpolation. The platform substitutes the current value at runtime.

```
Whenever the player uses <<skill_persuasion>>, apply a +1 bonus to the outcome.
```

For the full list of supported variable forms (tracked items, skills, `turn_number`, `random`, `XdY` dice, math operators) see `WORLD_JSON_SCHEMA_v2.4.md` §9.

**New in v2.2 — PawScript expressions.** The `<<…>>` interpolation syntax above is a **PawScript expression**: a read-only evaluation, legal anywhere adventure text is typed (`instructions`, `descriptionRequest`, tracked-item `description`, etc.). Expressions never mutate state — for that, see PawScript **scripts**, which run only inside `effectRunScript` trigger effects (§3 and `WORLD_JSON_SCHEMA_v2.4.md`'s `effectRunScript` row). Full PawScript syntax reference: https://infiniteworlds.app/pawscript-reference and https://infiniteworlds.app/pawscript-expressions-guide.

### Context provided to the AI each turn

The AI sees several predefined values every turn alongside the world fields you've authored:

| Variable | What it holds |
|---|---|
| `playerAction` | The text the player just submitted |
| `description` | The selected player character's `possibleCharacters[*].description` field (not the world-level `description`, which is the user-facing world-browser blurb) |
| `objective` | The world's current `objective` (mutable via `effectChangeObjective`) |
| `background` | The world's `background` (set at Start-of-Game; `effectChangeBackground` is SoG-only — see §7 and the SoG-only notes) |

If you write `instructions` that say "respond to the player's intent" — that intent is in `playerAction`. If you say "remind the player of their goal" — that's `objective`.

---

## 2. What the AI produces each turn (outcome fields)

The Storyteller AI emits a JSON object every turn with fields the platform parses and displays. Understanding this output shape is what lets you write `instructions` that meaningfully steer the AI.

### Narrative / decision fields

| Field | Type | Description |
|---|---|---|
| `evaluation` | string | Assessment of the player's action — typically `SUCCESS`, `FAILURE`, or `DENIED`. The world's `evaluationRequest` (if set) overrides the default evaluation rules. |
| `whereWhen` | string | Current time and location (e.g., `"11pm Friday, in the swamps"`). Tracked turn-to-turn; AI models often need help maintaining chronological consistency — see §4. |
| `outcomeDescription` | string | The main narrative response. Adheres to the world's `authorStyle`. This is what the player reads as the story. |
| `secretInfo` | string | Hidden lore and motivations the AI tracks for itself. Not shown to the player. Persists into future turns as context the AI considers. |
| `option1_text` / `option2_text` / `option3_text` | string | Three suggested next-move options shown to the player as quick-action buttons. |
| `stateVariablesUpdates` | object | Key-value pairs of tracked-item updates the AI is requesting based on what happened this turn. The platform validates these against the world's tracked items and their `updateInstructions`. |
| `triggerEvents` | string | Letters corresponding to any trigger events the AI judged were activated this turn — used by the engine to fire `triggerOnEvent` conditions. Distinct from the world-level `triggerEvents` array (which defines the triggers). |

### Illustration fields (drive image generation)

When the platform decides to render an illustration for the turn, the AI populates:

| Field | Type | Description |
|---|---|---|
| `illustrSubject` | string | Primary subject of the image. Never the player character unless explicitly requested — defaults to a scene element or NPC. |
| `illustrIsCharacter` | boolean | True if the subject is a person or creature; false for scenery. |
| `illustrAppearance` | string | Brief physical description (age, ancestry, hair/eyes/skin). |
| `illustrClothes` | string | Current clothing (excluding footwear by platform convention). |
| `illustrExpressionPosition` | string | Facial expression + body pose (e.g., `"friendly, sitting on a bench"`). |
| `illustrSetting` | string | Brief description of environment and time of day. |

The world's `imageStyleCharacterPre`/`Post` and `imageStyleNonCharacterPre`/`Post` (plus the newer `illustrationStyle*HighPriority`/`LowPriority` fields) wrap these AI-generated descriptors with platform-side LoRAs and style tags before the image model sees them.

---

## 3. Turn lifecycle (the order matters)

A single turn proceeds as a tightly-ordered sequence. Most authoring
confusion stems from misunderstanding this order.

### What happens in turn N

1. **Player submits an action** (`playerAction`).
2. **The Storyteller AI receives**: world `instructions`, the player
   action, the last 2–8 turns verbatim, and the Summary AI's running
   summary of earlier turns.
3. **The AI evaluates the action** against history and instructions
   (producing the `evaluation` field).
4. **The AI writes `outcomeDescription`** — the main narrative response,
   following `descriptionRequest` rules. Image-prompt instructions are
   processed in parallel here (filling the `illustr*` fields).
5. **The AI generates suggested next actions** (`option1_text`,
   `option2_text`, `option3_text`).
6. **The AI writes `secretInfo`** — hidden context for future turns.
7. **The AI fills `stateVariablesUpdates`** — proposed updates to tracked
   items, per their `updateInstructions`.
8. **The AI activates situation-based triggers** — emitted as the
   `triggerEvents` letters field, indicating which triggers' conditions
   it judges as satisfied this turn.
9. **The platform applies the emitted output**: writes the new tracked
   item values, evaluates all trigger conditions (including non-AI-judged
   ones like `triggerOnTurn` and `triggerOnTrackedItem`), and executes the
   effects of every trigger that fires — **including running any
   `effectRunScript` PawScript scripts attached to a firing trigger**
   (new in v2.2; see "PawScript scripts in the turn lifecycle" below).
10. **Every 6 turns from turn 8**, the Summary AI runs immediately after,
    updating the summary of the story so far per `summaryRequest`.

### The consequence

Steps 4–6 (the AI's narrative writing) happen *before* steps 7–9
(tracked-item updates and trigger effects). Any change to world state
introduced via tracked-item auto-update or trigger effect therefore
**does NOT influence the current turn's narrative** — the AI has already
written the turn by the time those changes occur. The earliest the AI
can react is turn N+1, when it reads the now-updated world state.

### Authoring pitfalls driven by turn lifecycle

- **`effectChangeBackground`, `effectChangeMainInstructions`,
  `effectChangeAuthorStyle`, `effectChangeObjective`, and
  `effectChangeDescriptionInstructions` don't retroactively reshape the
  current turn's narrative.** The AI wrote turn N using the *old* values.
  The new values influence turn N+1 onward. (Note: `effectChangeBackground`
  is **Start-of-Game-only** — it is silently ignored in regular mid-game
  triggers entirely; for mid-game context changes use
  `effectChangeMainInstructions`. See §7 and the SoG-only notes in
  `TRIGGER_EVENTS.md`.)
- **`effectTellAIWhatToDo` is a *next-turn* directive.** Its description
  specifies "one-turn instruction" — that's the *single turn after firing*,
  not the turn during which the trigger fired.
- **`effectShowMessage` *does* append to the current turn's
  `outcomeDescription`** — the platform tacks the message on at end-of-turn.
  But the surrounding narrative was written without knowledge of the
  append, so the message will read as tacked-on, not woven in. For
  narrative integration, set up the precondition in `instructions` or via
  a previous-turn trigger so the AI knows to write toward the moment.
- **`effectGiveInfo` adds to `secretInfo` for *future* turns.** The AI
  already wrote turn N's `secretInfo` before this effect fired.
- **`effectModifyKeywordBlock` won't fire for the current turn's
  context.** Even if the new keywords would match recent narrative, the
  block update happens after the AI is done — the new keywords/content
  are eligible starting turn N+1.
- **Tracked-item `updateInstructions` cannot make the AI follow new state
  on the same turn.** The AI writes `stateVariablesUpdates` in step 7,
  after `outcomeDescription` is locked. If you need the AI to know X
  before writing turn N, X must be in the world before turn N — via
  `instructions`, a tracked-item value set on turn N-1, or a trigger that
  fired on turn N-1.
- **Trigger chains don't collapse turns.** Trigger A → B via
  `triggerPrereqs` works (A's firing satisfies B's prereq within the same
  end-of-turn evaluation), but B's *effects* still won't influence the
  narrative until turn N+1.

### PawScript scripts in the turn lifecycle (new in v2.2)

`effectRunScript` runs a PawScript script when its trigger fires — same
step-9 timing as every other trigger effect, so the same consequence
applies: a script's mutations are not visible to the AI until turn N+1.

Scoping and safety rules that follow from where scripts sit in the
lifecycle:

- **Tracked items only.** A script may read and mutate tracked items (via
  their `variableName` `$handle`) but cannot touch `instructions`,
  character fields, trigger definitions, or any other world state. If you
  need to change non-tracked-item state, use the dedicated `effect*`
  types instead (`effectChangeMainInstructions`, `effectSetTrackedItemValue`,
  etc.) — a script cannot substitute for them.
- **Transactional.** If a script raises any error during execution,
  **none** of its changes are applied — the whole script's effect is
  rolled back as a unit. The error is logged to World Debug and **the
  game continues normally**; a failing script does not block or crash
  the turn.
- **No unbounded loops.** Scripts support bounded iteration over a
  tracked item's entries (`for each $x in $tracked_item_variable_name`)
  but must not contain open-ended loops. Author scripts assuming they run
  once, quickly, per trigger firing.
- **Expressions are a separate, read-only system.** Don't confuse
  `effectRunScript` (a mutating script, effects-only) with `<<…>>`
  PawScript expressions (read-only, legal in any adventure-text field —
  see §1). A script can contain expression-like reads, but the reverse
  isn't true: an expression typed into `instructions` cannot mutate a
  tracked item the way `effectRunScript` can.

See the `effectRunScript` row in `WORLD_JSON_SCHEMA_v2.4.md` §5 for the
data shape, and https://infiniteworlds.app/pawscript-script-guide for the
full scripting language reference.

### Documented behavior may evolve

This document describes the *expected* behavior of Infinite Worlds as
of v2.4. The platform updates over time, and specific behaviors may
shift. If observed behavior contradicts what's documented here — a
trigger firing on a different turn than expected, a tracked item not
updating as described, a different evaluation order — flag the
discrepancy to the user immediately rather than silently working around
it. Documentation drift is normal; surfacing it is how the docs stay
correct.

---

## 4. How `instructions` interact with output

The world's `instructions` field is the primary lever for shaping the fields above. Concretely:

- "Print the current time at the start of every outcome" → AI prepends a time stamp to `outcomeDescription`.
- "When the player attempts a deception, mark `evaluation` as DENIED if their `<<skill_charisma>>` is below 3" → AI uses the skill template variable in its evaluation logic.
- "Track the relationship between the player and Mira in `secretInfo`" → AI writes a running note into `secretInfo` each turn.

The world's `descriptionRequest` is a more surgical lever: it specifically overrides how `outcomeDescription` is composed (point of view, tense, naming rules, what to push into `secretInfo` vs the visible narrative). See [`WORLD_JSON_SCHEMA_v2.4.md`](../WORLD_JSON_SCHEMA_v2.4.md#1-top-level-fields) §1 for the field's exact role; this doc just notes that `descriptionRequest` lives downstream of `instructions` in the prompt pipeline and can therefore correct or constrain things `instructions` couldn't reach.

---

## 5. System mechanics

### Time tracking

The platform tracks the current time and location in the hidden `whereWhen` variable. The AI emits it every turn (e.g., `Mission Street, San Francisco, at 17:35 on Tuesday`).

**Authoring tactic.** AI models frequently lose chronological coherence — events slip out of order, days repeat, hours skip. Two reliable mitigations:

1. **Mandate explicit `whereWhen` rendering.** Write into `instructions` (or `descriptionRequest`) that the AI must print `whereWhen` at the beginning of `outcomeDescription` or `secretInfo` every turn. Visible state is easier for the AI to maintain than implicit state.
2. **Mirror time into a tracked item.** Create a tracked item with `dataType: "text"` and an `updateInstructions` that asks the AI to maintain a precise chronology there. Reference it via `<<timeline>>` (or whatever you name it) in subsequent instructions.

### Skill evaluation (default model)

When a player attempts an action, the AI:

1. Selects the most relevant skill from the world's `skills` array (and the active PC's skill ratings).
2. Estimates a *DifficultyScore* for the task (`0`–`5`).
3. Compares the PC's skill rating against the DifficultyScore to produce `evaluation`.

The platform's default skill scale:

| Rating | Meaning |
|---|---|
| 0 | Incapable |
| 1 | Incompetent |
| 2 | Unskilled |
| 3 | Competent |
| 4 | Highly Skilled |
| 5 | Exceptional |

**Common author overrides** (via `evaluationRequest` or `instructions`):

- **Multi-stage breakdown.** "Decompose complex actions into a sequence of sub-checks, evaluate each, then synthesize an overall outcome." Reduces the AI's bias toward all-or-nothing outcomes.
- **Stochastic checks.** "Add a `<<1d6>>` dice roll to the skill rating and compare against (DifficultyScore × 2)." Introduces variance and breaks the AI's tendency toward binary SUCCESS/FAILURE patterns.
- **Hidden Difficulty.** "Never reveal the DifficultyScore to the player; write it to `secretInfo` only." Preserves narrative tension.

When you override the skill system this aggressively, consider setting `hideSkillSystem: true` on the world so the platform's default skill UI doesn't conflict with your custom logic.

---

## 6. Author style guidelines

The `authorStyle` field is free-form prose that frames the AI's voice. Three principles:

- **Consistency over creativity.** If `authorStyle` says "Gritty Noir," the AI should hold that register even when the player's action invites a tonal shift. Reinforce the style in `instructions` for stronger adherence.
- **Higher-tier models are more proactive.** Premium models (e.g., Massivecat / Opus 4.5, Smilodon / Sonnet 4.5) drive narrative forward without explicit prompting from the player. Lower-tier models tend to wait. If your world depends on AI-initiated story beats, recommend a high-tier model via `recommendedAIModel`.
- **Descriptive depth belongs in `outcomeDescription`.** Sensory and emotional detail goes there. Keep `whereWhen` short (location + time clause) and `evaluation` to a single token. Authors who try to push poetic language into `evaluation` create downstream parsing problems for the platform.

---

## 7. Storyteller AI model roster (as of May 2026 — server-side, will drift)

> **Source:** IW community roster, May 2026. This section documents platform state, not schema-governed rules. Model availability changes over time and is not validated by the JSON Schema or this plugin. Treat this as a reference snapshot, not a canonical source — verify with the IW platform or community channels before relying on a specific model string.

### Currently active models

| IW Name | Underlying Model | Notes |
|---|---|---|
| **Smilodon** | Claude Sonnet 4.5 | Recommended all-rounder; Claude family |
| **Smilodon-thinking** | Claude Sonnet 4.5 (extended thinking) | Slower; deeper reasoning |
| **Massivecat** | Claude Opus 4.5 | Most powerful; expensive; Claude family |
| **Massivecat-thinking** | Claude Opus 4.5 (extended thinking) | |
| **Lynx** | Claude Haiku 4.5 | Low cost; Claude family |
| **Lynx-thinking** | Claude Haiku 4.5 (extended thinking) | |
| **Grimalkin** | GPT-4.1 | OpenAI model |
| **Leopard** | Gemini 2.5 Pro | Darker tone; tends to be harsh |
| **Leopard-2** | Gemini 3.1 Pro | Newer Leopard; less tested |
| **Wampus** | Aion-2.0 | Experimental; "turns things up to 11" |
| **Wildcat** | Hermes 3 405B | Budget option; decent creativity |
| **Tomcat** | Unknown | Very cheap; poor quality; testing only |
| **Caracal** | MiMo-V2.5-Pro | Confirmed active May 2026; Xiaomi model |

### Removed / no-longer-valid models

These strings have been removed from IW and will be **silently stripped on import** from `selectedAIProfiles` — do not use them there. Whether `recommendedAIModel` gets the same stripping is unverified: an *unknown* string demonstrably survives import in that field (Probe E, 2026-08-28 — see `PLATFORM_BEHAVIOR_NOTES.md`), so avoid retired names there too, but on general principle rather than observed stripping.

| IW Name | Was | Notes |
|---|---|---|
| **Lion** | Claude Sonnet 3.7 | **REMOVED** — stripped on import |
| **Lion-thinking** | Claude Sonnet 3.7 (extended thinking) | **REMOVED** |
| **Sabertooth** | Claude Sonnet 4.0 | Removed |
| **Sabertooth-thinking** | Claude Sonnet 4.0 (extended thinking) | Removed |
| **Panther** | Grok 4 | Removed |
| **Ocelot** / **Ocelot-new** / **Ocetoomuch** | DeepSeek R1 variants | Removed |
| **Tiger** | GPT-4o | Removed |
| **Gryphon** | Gemini 1.5 | Removed |
| **Shishi** | Qwen-2.5-Max | Removed |
| **Manticore** (as storyteller) | DeepSeek v3 | Removed as storyteller. **Note:** `imageModel: "manticore"` in world JSON refers to the image-generation model and remains valid — this is a separate system. |
| **Chimaera** | Random picker (Wildcat/Ocelot/Gryphon/Shishi) | Removed; all constituent models also removed |

### `selectedAIProfiles` — Claude-family only

`selectedAIProfiles` (used with `enableAISpecificInstructionBlocks: true`) is expected to accept only the **Claude family**: `smilodon`, `smilodon-thinking`, `massivecat`, `massivecat-thinking`, `lynx`, `lynx-thinking`. **Confirmed:** the removed `lion` / `lion-thinking` strings are invalid and stripped on import. The broader claim — that *all* non-Claude strings (including the otherwise-valid storyteller `tomcat`) are stripped from `selectedAIProfiles` — is **reported but import-test-pending**; treat it as the safe default (use only Claude-family strings here) until confirmed.

---

## 8. Cross-references

- **Trigger conditions and effects** — see `WORLD_JSON_SCHEMA_v2.4.md` §5 for the v2.4 canonical list, including the new `effectRunScript` type. The set of effect/condition types is the source of truth there, not in this document.
- **Template variables** — see `WORLD_JSON_SCHEMA_v2.4.md` §9 for the full `<<…>>` syntax.
- **Field allocation strategy** — see `FIELD_ALLOCATION_STRATEGY.md` for which kinds of content belong in which field (always-on `instructions` vs keyword-gated `loreBookEntries` vs trigger-gated effects).
- **PawScript scripting** — see `mechanics/PAWSCRIPT.md` for the full scripting model (syntax, tracked-item mutation rules, transactional semantics) and §3 above for how scripts fit into the turn lifecycle.
