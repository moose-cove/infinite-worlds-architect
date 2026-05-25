# AI Runtime Mechanics

This document explains what happens *at play time* when a player takes a turn in an Infinite Worlds story. The schema doc (`WORLD_JSON_SCHEMA_v2.1.md`) tells you what fields a world has and what shape they take. This doc tells you what the Storyteller AI actually does with them — what it produces each turn, how variables resolve, how skill checks are evaluated.

Read this before designing `instructions`, `authorStyle`, `descriptionRequest`, `evaluationRequest`, or any trigger effect that shapes AI output. If you don't understand what the AI emits, you can't usefully constrain it.

---

## 1. Instruction syntax

### Template variables — `<<name>>`

Any text field in the world JSON (and most trigger-effect string fields) supports `<<variable>>` interpolation. The platform substitutes the current value at runtime.

```
Whenever the player uses <<skill_persuasion>>, apply a +1 bonus to the outcome.
```

For the full list of supported variable forms (tracked items, skills, `turn_number`, `random`, `XdY` dice, math operators) see `WORLD_JSON_SCHEMA_v2.1.md` §9.

### Context provided to the AI each turn

The AI sees several predefined values every turn alongside the world fields you've authored:

| Variable | What it holds |
|---|---|
| `playerAction` | The text the player just submitted |
| `description` | The selected player character's `description` |
| `objective` | The world's current `objective` (mutable via `effectChangeObjective`) |
| `background` | The world's current `background` (mutable via `effectChangeBackground`) |

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

## 3. How `instructions` interact with output

The world's `instructions` field is the primary lever for shaping the fields above. Concretely:

- "Print the current time at the start of every outcome" → AI prepends a time stamp to `outcomeDescription`.
- "When the player attempts a deception, mark `evaluation` as DENIED if their `<<skill_charisma>>` is below 3" → AI uses the skill template variable in its evaluation logic.
- "Track the relationship between the player and Mira in `secretInfo`" → AI writes a running note into `secretInfo` each turn.

The world's `descriptionRequest` is a more surgical lever: it specifically overrides how `outcomeDescription` is composed (point of view, tense, naming rules, what to push into `secretInfo` vs the visible narrative). See [`WORLD_JSON_SCHEMA_v2.1.md`](./WORLD_JSON_SCHEMA_v2.1.md#1-top-level-fields) §1 for the field's exact role; this doc just notes that `descriptionRequest` lives downstream of `instructions` in the prompt pipeline and can therefore correct or constrain things `instructions` couldn't reach.

---

## 4. System mechanics

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

## 5. Author style guidelines

The `authorStyle` field is free-form prose that frames the AI's voice. Three principles:

- **Consistency over creativity.** If `authorStyle` says "Gritty Noir," the AI should hold that register even when the player's action invites a tonal shift. Reinforce the style in `instructions` for stronger adherence.
- **Higher-tier models are more proactive.** Premium models (e.g., "Lion", "Smilodon" tiers) drive narrative forward without explicit prompting from the player. Lower-tier models tend to wait. If your world depends on AI-initiated story beats, recommend a high-tier model via `recommendedAIModel`.
- **Descriptive depth belongs in `outcomeDescription`.** Sensory and emotional detail goes there. Keep `whereWhen` short (location + time clause) and `evaluation` to a single token. Authors who try to push poetic language into `evaluation` create downstream parsing problems for the platform.

---

## 6. Cross-references

- **Trigger conditions and effects** — see `WORLD_JSON_SCHEMA_v2.1.md` §5 for the v2.1 canonical list. The set of effect/condition types is the source of truth there, not in this document.
- **Template variables** — see `WORLD_JSON_SCHEMA_v2.1.md` §9 for the full `<<…>>` syntax.
- **Field allocation strategy** — see `FIELD_ALLOCATION_STRATEGY.md` for which kinds of content belong in which field (always-on `instructions` vs keyword-gated `loreBookEntries` vs trigger-gated effects).
