# Field Guide: Tracked Items

JSON key: `trackedItems` — array of tracked item objects. For exact field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../../WORLD_JSON_SCHEMA_v2.1.md#4-trackeditems) §4.

This file covers *authoring judgments* about tracked items: when to use them, how to choose `dataType` and `visibility`, what `updateInstructions` actually shape.

---

## What tracked items do

Tracked items are author-defined variables the storyteller AI monitors and updates each turn. They store state: player resources, relationship scores, flags, inventory, time, structured data. The AI reads current values each turn and writes updates to `stateVariablesUpdates` in its response.

**Per-turn processing cost.** The AI must process all tracked items every turn (read current value, decide whether to update, write updates if so). This has two implications:

- **There is an effective 10,000-character output limit per tracked item.** If a single item's value would exceed this, the AI's update will be truncated.
- **Avoid tracking flavor.** If a variable doesn't gate a trigger, factor into a skill check, or surface in narrative via `<<var>>` interpolation, consider whether it needs to be tracked at all. Every tracked item costs tokens forever.

**Update timing.** Auto-updates are written by the Storyteller AI *after*
it has finished writing `outcomeDescription` and `secretInfo` for the turn
(step 7 of the per-turn sequence — see
[`AI_RUNTIME_MECHANICS.md`](../../mechanics/AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
§3). The AI cannot read a tracked item's just-updated value during the
same turn — it only sees the new value starting turn N+1.

**Pitfall.** Don't write `updateInstructions` that the AI is supposed to
obey *on the same turn the update happens*. If you need the AI to know X
before writing turn N, X must be in the world before turn N — via
`instructions`, via a tracked-item value updated on turn N-1, or by a
trigger that fired on turn N-1.

---

## Choosing `dataType`

| `dataType` | Use for | Notes |
|---|---|---|
| `text` | Inventory lists, location names, qualitative states ("hungry", "wounded"), comma-separated tags | Most flexible. Text items support `contains` comparison in `triggerOnTrackedItem`. |
| `number` | Health, gold, turn counters, skill scores, relationship meters | Required for arithmetic operations and the `at_least` / `is_exactly` / `at_most` operators. |
| `xml` | Complex nested state — multi-dimensional spell effects, structured records, mini-databases | Authors must understand XML formatting. The AI handles XML literally — malformed XML stays malformed. |

If you're uncertain whether something should be `number` or `text`: pick `number` if you'll ever compare it (`at_least 50` etc.). Pick `text` if you only need equality or substring matching.

---

## Choosing `visibility`

The v2.1 enum: `everyone`, `ai_only`, `ai_only_boring`, `player_only`, `hidden`.

| Value | Who sees the value | When to use |
|---|---|---|
| `everyone` | Player (UI) and AI (every turn) | HUD items the player should monitor: gold, health, inventory, objective progress. |
| `ai_only` | AI only (every turn) | Hidden state the AI uses for decisions but the player shouldn't see: internal counters, secret relationship scores, plot flags. |
| `ai_only_boring` | AI only (every turn) | Equivalent to `ai_only` in current platform behavior — both forms appear in real exports. Accept whichever the input used and preserve it on round-trip. |
| `player_only` | Player (UI) only | Rare. Used when the player should track something the AI shouldn't reason about. |
| `hidden` | Nobody automatically | Mechanical state only modified and read by trigger effects. The AI cannot auto-update items it cannot see. |

**v2.1 rename.** Pre-v2.1 worlds used `nobody` for what is now `hidden`. If you encounter `nobody` in a legacy world, treat it as `hidden`. The plugin's validator preserves unrecognized values on round-trip, but new worlds should use the v2.1 enum.

**The visibility trap.** Items with visibility `player_only` or `hidden` are **invisible to the AI**, which means the AI cannot auto-update them via `updateInstructions`. They can only be modified by trigger effects (`effectSetTrackedItemValue`). If you set `visibility: "hidden"` and then write detailed `updateInstructions`, those instructions are a no-op.

---

## Writing `updateInstructions`

`updateInstructions` is the AI's direct rulebook for the item. The AI follows these literally — precise wording matters.

**Good patterns:**
- `"Update whenever the player gains, earns, spends, or loses gold."` — clear trigger conditions, exhaustive verb list.
- `"ALWAYS increase this counter by 1 every turn."` — uppercase emphasis for unconditional rules.
- `"Set to the current location at the end of each turn."` — declarative, no ambiguity.
- `"Add items when picked up, remove items when used or dropped. Format: comma-separated list."` — both the action and the storage format.

**Bad patterns:**
- `"Track the player's mood."` — too vague; the AI will guess at what "track" and "mood" mean.
- `"Update appropriately based on context."` — non-instructions.

**Disabling auto-update.** Set `autoUpdate: false` to take the item out of the AI's hands entirely. The item is then only modified by trigger effects. Use when you need deterministic, trigger-driven changes rather than AI-interpreted ones.

---

## Initial values

- **`initialValue`** — the world-default starting value, applied to all PCs unless overridden.
- **`initialValueBasedOnPC`** — `"same"` (all PCs share `initialValue`), `"character"` (per-PC defaults from `possibleCharacters[*].initialTrackedItemValues`), or `"player"` (player picks at game start from the per-PC array of choices).
- **`possibleCharacters[*].initialTrackedItemValues[*].initialPCValue`** can be a **string OR a string array**. When it's an array (e.g., `["0", "900", "5"]`), those are the *choices* the player picks from at character selection — not a `[min, max, default]` tuple. Treat the array as an unordered set of valid options.
  - **Single value vs. selection menu.** A scalar string is a fixed starting value. An array is a **pick-one menu**: the player selects exactly one option at character creation, and that single choice becomes the item's active value. The item never holds every option at once.
  - **Consequence for triggers.** Because the active value is the one chosen option, a `triggerOnTrackedItem` condition evaluates against that single choice — *not* against the whole option list. A `contains` test is **not** automatically satisfied just because the menu happens to list the required string. See [`TRIGGER_EVENTS.md`](./TRIGGER_EVENTS.md#choosing-condition-types).

---

## Practical guidance

**Use `secretInfo` instead of tracked items when you can.** Authors sometimes simulate tracked items by writing values into `secretInfo` via `descriptionRequest`. This avoids the per-turn processing cost. Trade-off: `secretInfo` is not directly accessible to trigger conditions — you can't gate a trigger on a `secretInfo` value the way you can with `triggerOnTrackedItem`.

**Visibility strategy:**
- Player-visible items create a visible HUD — use for resources and statuses the player should actively monitor.
- AI-only items let you track state the player shouldn't see but the AI needs (hidden plot flags, internal counters).
- `hidden` items are only useful when trigger effects both set and read them — purely mechanical state.

**Cross-reference for trigger interaction.** Tracked items pair tightly with `triggerOnTrackedItem` conditions (for gating) and `effectSetTrackedItemValue` / `effectModifyTrackedItemDetails` effects (for modification). When designing a tracked item, consider what conditions will read it and what effects will write it — if neither exists, the item is dead weight.

See also: [`FIELD_ALLOCATION_STRATEGY.md`](../../guidance/FIELD_ALLOCATION_STRATEGY.md) on when to choose a tracked item vs. embedding state in `secretInfo` or `background`.
