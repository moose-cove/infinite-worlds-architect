# Field Guide: Trigger Events

JSON key: `triggerEvents` — array of trigger objects.

For the canonical list of v2.1 condition types and effect types with their `data` shapes, see [`WORLD_JSON_SCHEMA_v2.1.md`](../../WORLD_JSON_SCHEMA_v2.1.md#5-triggerevents). This file covers *authoring judgments* — when to use which option — not the type catalog.

---

## How triggers work

Triggers evaluate and fire **after the Storyteller AI has finished writing
the turn's narrative** — they're step 9 of the per-turn sequence (see
[`AI_RUNTIME_MECHANICS.md`](../../mechanics/AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
§3 for the full lifecycle). This is the single most important fact about
triggers — most authoring mistakes stem from forgetting it.

**The consequence.** Every trigger effect — narrative replacement,
world-state change, tracked-item modification, KIB swap, character change —
only becomes visible to the storyteller on the **next** turn. A trigger
that fires on turn 5 has no influence on turn 5's narrative. The new state
is what the storyteller sees on turn 6.

The one exception is `effectShowMessage`, which appends text to the current
turn's `outcomeDescription` after the AI is done writing — the appended
text appears in the current turn's displayed output, but the surrounding
narrative was written without it.

See `AI_RUNTIME_MECHANICS.md` §3 (Turn lifecycle — Authoring pitfalls) for
the concrete failure modes this causes.

All conditions on a single trigger evaluate with AND logic — every
condition must be satisfied simultaneously for the trigger to fire. When
the conditions are met, all of the trigger's effects execute (in trigger-
list order).

**Default behavior.** A trigger fires at most **once per playthrough**.
Set `canTriggerMoreThanOnce: true` to allow it to fire on every eligible
turn.

---

## Meta-fields

### `canTriggerMoreThanOnce`
- `false` (default): fires exactly once, then never again — even if conditions are met again. Use for one-time plot beats.
- `true`: fires every turn its conditions are met. Use for recurring mechanics, ambient effects, periodic state shifts.

### `triggerPrereqs` (condition type, not a top-level field)
Listed under `triggerConditions` with `category: "condition"`, `type: "triggerPrereqs"`, and `data: string[]` of trigger IDs. The named triggers must have already fired before this one becomes eligible.

If a prerequisite fires on the same turn, it only satisfies the condition if it appears earlier in the trigger list.

### `triggerBlockers` (condition type)
Same shape as `triggerPrereqs`. The named triggers must NOT have fired previously. If any have fired, this trigger is permanently blocked.

**Reference by ID, not by name.** Both `triggerPrereqs` and `triggerBlockers` reference trigger `id` values, not trigger `name` values. Use `mint_ids("triggerEvent", n)` to allocate IDs, and keep a mapping handy while authoring.

---

## Choosing condition types

| When you need… | Use |
|---|---|
| AI-judged event in the narrative | `triggerOnEvent` — natural-language description. **Max 10 per world.** Each costs an extra AI evaluation per turn. |
| Specific turn number (or "after turn N") | `triggerOnTurn` — integer. Combine with `canTriggerMoreThanOnce: true` for recurring beats from a turn onward. |
| Game-start setup | Top-level `triggerOnStartOfGame: true` on the trigger itself (not a `triggerConditions` entry). |
| Restriction to specific player characters | `triggerOnCharacter` — array of `characterId` values from `possibleCharacters`. |
| State-based gating (number/text/XML comparison) | `triggerOnTrackedItem` — supports `at_least`, `is_exactly`, `at_most` (numbers), `contains` (text/XML). Supports compound logic via `category: "logic"` with `and`/`or`. |
| Probabilistic firing | `triggerOnRandomChance` — formula string (e.g., `"30"` for 30%, or `"15+round(turn_number%random)"` for dynamic). |
| Chained triggers | `triggerPrereqs` and `triggerBlockers` (see meta-fields above). |

`triggerOnEvent` is the most flexible but also the noisiest. The AI's evaluation can produce false positives (firing when the situation didn't really occur) and false negatives (failing to fire when it did). Use very explicit language and prefer concrete cues over abstract ones. "The player has explicitly handed the dagger to Mira" is more reliable than "The player has surrendered."

---

## Choosing effect types — when to use which

The full list lives in the schema doc. The authoring judgments below address *which to pick when multiple could plausibly do the job*.

### Narrative-shaping effects

| Effect | Reliability | Best for |
|---|---|---|
| `effectShowMessage` | High (mechanical append) | Scripted narrative beats. Text appends directly to `outcomeDescription`. Use when you want exact prose to appear verbatim. |
| `effectTellAIWhatToDo` | **Highest** (directive) | The most reliable effect for steering the AI. One-turn instruction — active for the immediate next turn, then discarded. Use when the AI *must* do something specific. |
| `effectGiveInfo` | Medium (suggestive) | Appended to `secretInfo`. The AI considers it but is not obligated to act on it. Use for world-state context the AI should be aware of but not necessarily act on this turn. |

The reliability gradient is critical. Authors who use `effectGiveInfo` to enforce behavior find the AI ignores it; authors who use `effectTellAIWhatToDo` for ambient context find it overrides everything else for that turn. Pick the right tool.

### World-state replacement effects

**Important: world-state replacement effects do not auto-revert.** Each of
the effects below fully replaces the corresponding world field. Once fired,
the original value is gone — to restore it later, you must explicitly
author another trigger that re-installs the old value. This applies to
`effectChangeBackground`, `effectChangeMainInstructions`,
`effectChangeAuthorStyle`, `effectChangeDescriptionInstructions`,
`effectChangeObjective`, and `effectChangeFirstAction`. Use them
deliberately; one-shot "fire and forget" replacements leave the world
permanently in the new state for the rest of the playthrough.

**Scope restriction:** `effectChangeBackground` and `effectChangeFirstAction` are **Start-of-Game (SoG) only**. Confirmed by IW import testing (May 2026): IW silently ignores these effects in regular (mid-game) triggers. For mid-game context or setting changes, use `effectChangeMainInstructions` instead. (Even if IW permitted mid-game `effectChangeBackground`, the effect would be inert: `background` is only sent to the storyteller AI at turn 0 and is superseded by the Summary AI's running summary after ~turn 8.)

| Effect | Replaces | Notes |
|---|---|---|
| `effectChangeBackground` | `background` | **SoG-only** — silently ignored in regular triggers |
| `effectChangeMainInstructions` | `instructions` | Use cautiously — overrides the whole block; preferred alternative for mid-game context changes |
| `effectChangeAuthorStyle` | `authorStyle` | Great for genre transitions mid-story |
| `effectChangeDescriptionInstructions` | `descriptionRequest` | |
| `effectChangeObjective` | `objective` | AI prioritizes objective heavily — most powerful silent story-redirection lever |
| `effectChangeFirstAction` | `firstInput` | **SoG-only** — only meaningful in `triggerOnStartOfGame` triggers |
| `effectChangeVictoryCondition` | `victoryCondition` | Engine-only — no narrative effect |
| `effectChangeDefeatCondition` | `defeatCondition` | Engine-only |
| `effectModifyInstructionBlock` | A specific Extra Instruction Block by `id` | Surgical alternative to `effectChangeMainInstructions` |
| `effectModifyKeywordBlock` | A specific Keyword Instruction Block by `id` | Replaces both `keywords` and `content` |

`effectChangeObjective` is underused. The AI strongly weights the current objective when deciding what to narrate, so quietly swapping the objective at a plot transition is one of the most powerful authoring techniques — the player sees a UI update and feels the story shift naturally.

### Character effects

| Effect | Use for |
|---|---|
| `effectChangePCName` | Renaming the active PC mid-game (transformation, alias reveal, marriage). |
| `effectChangePCDescription` | Replacing the active PC's description text. |
| `effectChangePCSkill` | Adjusting one skill at a time. `data: {name, amount, minmax, increase}`. One skill per effect — use multiple effects to adjust several skills in the same trigger. |

### Tracked-item effects

| Effect | Use for |
|---|---|
| `effectSetTrackedItemValue` | Single-item update. Data shape varies by `action`: `set` / `add` / `subtract` for numbers; `set` / `add` (append) / `subtract` (remove if present) / `replace` (find-and-replace via `replaceWith`) for text/XML. Supports `<<item_name>>` interpolation in values. **`replaceWith` must be present in `data` for every action** (use `""` when unused) — omitting it may break import. It is only *consumed* by the `replace` action, but the field itself is required regardless of action type. |
| `effectModifyTrackedItemDetails` | Modify the item's *definition* (name, description, visibility, updateInstructions, autoUpdate) — not its value. Override flags control which fields are changed. |

### Interactive effects (blocking — pause until player responds)

| Effect | Use for |
|---|---|
| `effectPresentChoice` | Multiple-choice picker. Result written to `targetTrackedItemId`. Supports single/multi-select. Useful when the player must make a specific decision the AI couldn't reliably extract from free text. |
| `effectRequestInput` | Free-text input. Result written to `targetTrackedItemId`. |

Both pause gameplay until the player responds. Use sparingly — they break narrative flow.

### End-game effects

| Effect | Use for |
|---|---|
| `effectEndsGame` | End the game from inside a trigger. `data: true` → game ends and the player can choose to continue (victory-style). `data: false` → game ends with no continuation (defeat-style; restart only). Pair with `effectShowMessage` in the same trigger to explain the ending to the player. |

Note: pre-v2.1 worlds used a separate `canContinueEndedGame` boolean field
for the continuation control; in v2.1 the two have been folded into the
single `data` boolean above. Authors familiar with the wiki's older
documentation will not find `canContinueEndedGame` in v2.1 fixtures.

Top-level `victoryCondition` and `defeatCondition` fields provide the
built-in end-game system (victory auto-allows continuation; defeat does
not). Use `effectEndsGame` for custom end conditions — multiple ending
branches, conditional victory/defeat, or non-standard continuation
behavior. See [`VICTORY_DEFEAT.md`](VICTORY_DEFEAT.md) for the full
comparison.

---

## Key constraints

1. **AND logic only.** All conditions on one trigger must be met simultaneously. For OR logic, create multiple triggers (or use `category: "logic"` with `operator: "or"` when `advancedLogic: true`).
2. **Evaluation order matters.** `triggerPrereqs` and `triggerBlockers` only recognize triggers that fired earlier in the same evaluation pass (same turn, earlier in the list). Trigger ordering is therefore semantically significant.
3. **`triggerOnEvent` limit.** Maximum 10 AI-evaluated event conditions per world. Each one is paid for in additional AI evaluation tokens every turn.
4. **Pre-game triggers (`triggerOnStartOfGame: true`).** Fire before turn 0, before the player acts. Some effects (notably `effectTellAIWhatToDo`) behave differently or are no-ops in this context — the "next turn" they target is turn 1, not turn 0.

---

## Variable replacement in effect data

The `<<item_name>>` syntax works in all effect data string fields. References resolve at runtime using the current value of the named tracked item (spaces become underscores, lowercase). Math and dice functions also work — `<<1d20>>`, `<<gold * 2>>`, `<<round(turn_number/3)>>`. See [`WORLD_JSON_SCHEMA_v2.1.md`](../../WORLD_JSON_SCHEMA_v2.1.md#9-template-variable-system) §9 for the full template-variable system.
