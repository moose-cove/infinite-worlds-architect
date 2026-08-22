# Field Guide: Trigger Events

JSON key: `triggerEvents` — array of trigger objects.

For the canonical list of v2.4 condition types and effect types with their `data` shapes, see [`WORLD_JSON_SCHEMA_v2.4.md`](../../WORLD_JSON_SCHEMA_v2.4.md#5-triggerevents). This file covers *authoring judgments* — when to use which option — not the type catalog.

---

## How triggers work

Triggers evaluate and fire **after the Storyteller AI has finished writing
the turn's narrative** — they're step 9 of the per-turn sequence (see
[`AI_RUNTIME_MECHANICS.md`](../mechanics/AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
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
Listed under `triggerConditions` with `category: "condition"` and `type: "triggerPrereqs"`. The named triggers must have already fired before this one becomes eligible.

**Schema v2.4 changed `data` from a bare array to an object:**

```jsonc
// pre-v2.4                     // v2.4 — emit this
"data": ["PKRVGe1E"]            "data": { "prereqs": ["PKRVGe1E"], "firedThisTurn": false }
```

If a prerequisite fires on the same turn, it only satisfies the condition if it appears earlier in the trigger list.

### `triggerBlockers` (condition type)
Same shape as `triggerPrereqs`, with the array under `blockers` instead of `prereqs`. The named triggers must NOT have fired previously. If any have fired, this trigger is permanently blocked.

```jsonc
"data": { "blockers": ["PKRVGe1E"], "firedThisTurn": false }
```

**`firedThisTurn` is still an open question — emit `false`.** The canonical fixture shows only `false`, on both condition types.

The documented default behaviour gives the guess its shape. The wiki describes prereqs as *"met if all of the selected triggers have fired at least once in **any previous turn**"* and blockers as *"met if one or more of the selected triggers **has ever** fired"* (wiki-sourced, and predating v2.4). So the baseline really is "at any point in the past", which makes "`firedThisTurn` toggles exactly that" the most plausible reading — but plausible is not verified, and the platform's behaviour when it is `true` is untested.

A round trip narrowed this without closing it: `firedThisTurn: true` **survived import unchanged**, so it is at minimum author-writable and not reset on the way in. That weakens the competing reading — that it is platform-managed runtime state the exporter writes — without killing it, since a value can be stored on import and still overwritten at runtime. Its *meaning* remains untested.

The advice is unchanged: **emit `false`**, and don't set `true` unless the author has confirmed the behaviour in-game.

**Migrate a legacy bare array BEFORE importing — the platform destroys it.** Confirmed 2026-08-06 by round trip: IW does not migrate the pre-v2.4 shape. It **deletes the condition outright**, leaving `"triggerConditions": []` with the trigger's ID, name and effects intact. The result is an ungated trigger, with no error in-game and none in the export. Two same-anchor gates in the v2.4 object form round-tripped byte-identical in the same import, so the bare array is definitively the cause.

The failure is unusually hard to notice, because the damage erases its own evidence: the re-exported world validates with *fewer* warnings than the input, since the legacy-shape message has nothing left to fire on. A world can look cleaner after losing its gates.

The plugin's validator still **reads** both shapes — resolving trigger IDs through either, so a shape change never silently disables the dangling-reference check. Severity is version-conditional: a world declaring `schemaVersion` 2.4 or higher while carrying a v2.2 gate shape is self-contradictory and **errors**; a world honestly declaring 2.2 or lower gets the same message as a **warning**. That split is what keeps `example-world-schema-v2.1.json` and `example-world-schema-v2.2.json` validating with warnings only — they are the only regression coverage for reading the legacy shape at all.

**Reference by ID, not by name.** Both `triggerPrereqs` and `triggerBlockers` reference trigger `id` values, not trigger `name` values. Use `mint_ids("triggerEvent", n)` to allocate IDs, and keep a mapping handy while authoring.

### Top-level `conditions` — the named-event registry (v2.4)

Schema v2.4 adds a top-level `conditions: string[]` to the world. Each entry is a natural-language event description, and it is the *declaration* half of `triggerOnEvent`:

```jsonc
"conditions": ["The marmut eats the marmalade"],
// …
{ "type": "triggerOnEvent", "category": "condition", "data": "The marmut eats the marmalade" }
```

**Exact-text keying is well-supported.** The fixture's one entry matches its one `triggerOnEvent` `data` string byte-for-byte, and nothing else links them — no ID, no index — so text is the only available key. Case, internal whitespace and trailing punctuation are all significant; the plugin applies no normalization beyond trimming outer whitespace, because the platform's own matching rule is undocumented and inventing one would trade missed warnings for false ones.

**The registry is author-maintained.** Confirmed 2026-08-06 by round trip: a world went in with one event *used but not declared* and one entry *declared but unused*, and `conditions` came back byte-identical — the platform neither added the missing entry nor pruned the orphan. It does not regenerate the array, so keeping it in sync is the author's job (and the plugin's).

This also closes off the competing reading, under which the platform derived `conditions` from the `triggerOnEvent` strings already in use. That reading was the only available explanation for how the ten-event cap gets enforced, so ruling it out reopens the cap question — see below.

**When adding a `triggerOnEvent`, add its exact text to `conditions` in the same edit.** Pre-v2.4 worlds have no `conditions` array at all, so migrating one surfaces a warning per `triggerOnEvent` — that is the intended nudge, and the fix is to collect the event strings into a new `conditions` array. The validator warns in the reverse direction too, on a declared entry no `triggerOnEvent` uses: a dead dropdown entry. Both stay warnings, never errors — a desync costs editor selectability, not correctness.

**The cap is ten, and it is not applied at import.** `validate_world` warns past it. A world carrying twelve declared events and twelve matching triggers round-tripped with all twelve intact — nothing was rejected and nothing truncated. Combined with the author-maintained finding above, both import-side enforcement mechanisms are ruled out, so the cap is either applied at runtime or is purely advisory; that is still untested. Each AI-evaluated event costs an extra AI evaluation every turn regardless, so treat ten as a cost ceiling even if it proves not to be a hard limit.

---

## Choosing condition types

| When you need… | Use |
|---|---|
| AI-judged event in the narrative | `triggerOnEvent` — natural-language description. **Max 10 per world.** Each costs an extra AI evaluation per turn. v2.4: also declare the event text in the top-level `conditions` array. |
| Specific turn number (or "after turn N") | `triggerOnTurn` — integer. Combine with `canTriggerMoreThanOnce: true` for recurring beats from a turn onward. |
| Game-start setup | Top-level `triggerOnStartOfGame: true` on the trigger itself (not a `triggerConditions` entry). |
| Restriction to specific player characters | `triggerOnCharacter` — array of `characterId` values from `possibleCharacters`. |
| State-based gating (number/text/XML comparison) | `triggerOnTrackedItem` — supports `at_least`, `is_exactly`, `at_most` (numbers), `contains` (text/XML). Supports compound logic via `category: "logic"` with `and`/`or`. |
| Scripted state test (compound, arithmetic, or YAML sub-field) | `triggerOnPawScript` — `data` is one PawScript boolean expression, e.g. `$favorite_flavor = "Lemon"` or `$gold >= 50 and $puppies.count > 2`. Evaluated deterministically each turn against live tracked-item values (`$variableName` form, not `<<…>>`). Reach for it instead of stacking `triggerOnTrackedItem` under a `logic` node once the test has more than one clause or needs a computed value. Not AI-evaluated, so presumed **not** to count toward the ten-event cap (unverified). Every `$name` must be a tracked item's `variableName` or a native — the validator warns on anything else. See [`PAWSCRIPT.md` §3](../mechanics/PAWSCRIPT.md#3-expressions-). |
| Probabilistic firing | `triggerOnRandomChance` — formula string (e.g., `"30"` for 30%, or `"15+round(turn_number%random)"` for dynamic). The formula can read a tracked item as `$variableName` — fixture 1.1 uses `"$number_of_non_human_friends+round(turn_number%random)"` so the chance grows with state. That is the idiom for "chance scales with X"; it does not need a `triggerOnPawScript` plus a separate roll. `turn_number` and `random` stay bare (no `$`) in this field. The validator warns on a `$name` that is not a `variableName` or native. |
| Chained triggers | `triggerPrereqs` and `triggerBlockers` — v2.4 object shape `{prereqs\|blockers: [...], firedThisTurn: false}` (see meta-fields above). |

`triggerOnEvent` is the most flexible but also the noisiest. The AI's evaluation can produce false positives (firing when the situation didn't really occur) and false negatives (failing to fire when it did). Use very explicit language and prefer concrete cues over abstract ones. "The player has explicitly handed the dagger to Mira" is more reliable than "The player has surrendered."

**`triggerOnTrackedItem` evaluates the *current* value, not the menu of possible values.** When a tracked item's per-character `initialPCValue` is a string array, that array is a **pick-one selection menu** — the player chooses one option at character selection and that single choice becomes the active value (see [`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md#initial-values)). The condition is tested against the player's chosen value, so a `contains` test is **not** always-true just because the option list happens to include the `requiredValue`. Reason about *which single option* satisfies the condition. For example, an item with menu `["Basic Images", "Premium Advanced Images"]` and a `contains: "Basic Images"` condition fires **only** for players who picked Basic Images — not for everyone, and not at all for players who picked Premium Advanced Images.

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
| `effectRunScript` (v2.2) | Bulk or structured mutation across one or more tracked items. `data` is a PawScript string that runs when the trigger fires. **Can only mutate tracked items** — no narrative output, no world-field changes, no calling other effects. Transactional: if the script errors partway through, the whole run is rolled back (no partial mutation), the error is logged to World Debug, and the game continues normally. No unbounded loops — iterate over list/map contents (`for each $x in $list`) or a bounded `range(n)`, never an open-ended condition. |

**Choosing between `effectSetTrackedItemValue` and `effectRunScript`:** use `effectSetTrackedItemValue` for a single scalar set/add/subtract on one tracked item — it's simpler to author and read in the trigger list. Reach for `effectRunScript` once the update is deterministic bookkeeping across *multiple* values or *structured* (YAML) data — incrementing several stats in one pass, updating every entry in a list, or mutating nested fields on a YAML tracked item. Anywhere the update logic would otherwise require several `effectSetTrackedItemValue` effects chained together, or would require the AI to compute the new value itself via `updateInstructions`, `effectRunScript` gets the same result deterministically and in one effect. See [`SURVIVAL_STATS.md`](../patterns/SURVIVAL_STATS.md) for a worked example of migrating AI-computed bookkeeping to a scripted, deterministic pattern.

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
3. **`triggerOnEvent` limit.** Maximum 10 AI-evaluated event conditions per world — documented, but **not enforced at import** (twelve round-tripped untruncated; see the cap discussion above). Treat it as a cost ceiling rather than a hard limit: each one is paid for in additional AI evaluation tokens every turn.
4. **Pre-game triggers (`triggerOnStartOfGame: true`).** Fire before turn 0, before the player acts. Some effects (notably `effectTellAIWhatToDo`) behave differently or are no-ops in this context — the "next turn" they target is turn 1, not turn 0.

---

## Variable replacement in effect data

The `<<item_name>>` syntax works in all effect data string fields. References resolve at runtime using the current value of the named tracked item (spaces become underscores, lowercase). Math and dice functions also work — `<<1d20>>`, `<<gold * 2>>`, `<<round(turn_number/3)>>`. See [`WORLD_JSON_SCHEMA_v2.4.md`](../../WORLD_JSON_SCHEMA_v2.4.md#9-template-variable-system) §9 for the full template-variable system.
