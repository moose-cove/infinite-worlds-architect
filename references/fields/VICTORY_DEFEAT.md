# Field Guide: Victory and Defeat Conditions

Covers both end-game systems available in v2.4:
- Top-level `victoryCondition` and `defeatCondition` fields (the built-in
  end-game system).
- Trigger-based end-game via the `effectEndsGame` effect.

For field shapes see [`WORLD_JSON_SCHEMA_v2.4.md`](../../WORLD_JSON_SCHEMA_v2.4.md#1-top-level-fields) §1 (top-level conditions) and §5 (effect types).

---

## Critical: the storyteller AI cannot see these conditions during play

> "The storyteller AI does not receive these triggers with any special context, and therefore is not influenced by their contents in any way while writing outputs."

Victory and defeat conditions are evaluated by the **platform's game engine**, not by the storyteller AI. The AI writes narrative without any awareness of these fields. This means:

- Writing "when the player defeats the villain" in `victoryCondition.condition` does **not** make the AI work toward or narrate a villain defeat.
- The conditions only end the game when the engine's evaluation determines they're met.
- The AI does not steer the story toward victory or away from defeat based on these fields.

**For AI narrative steering**, use `objective` (always-on goal) and `effectTellAIWhatToDo` trigger effects instead. The objective is what the AI optimizes for narratively; victory/defeat conditions are mechanical end-state checks.

---

## System 1: Top-level `victoryCondition` / `defeatCondition`

The built-in end-game system. Each is an object of shape `{condition: string, text: string, alreadyFired: boolean}`.

| Sub-field | Type | Notes |
|---|---|---|
| `condition` | string | Free-form English expression the engine evaluates each turn. |
| `text` | string | Message shown to the player when the condition fires. |
| `alreadyFired` | boolean | Platform runtime state. **Never write `true` from the plugin** — this is a runtime flag the platform sets when the condition has already triggered. |

Either field may be `null` if the world has no configured victory/defeat (some worlds disable the system entirely and rely on triggers).

### Defaults

If `victoryCondition` is left at the platform default (with empty `condition`):
- Default condition: "The player character has succeeded in their initial goals" (contextualised to the original world-design prompt at generation time).
- Default `text`: "Congratulations! You have been successful in your adventure." (also contextualised to the original prompt when auto-generated).

If `defeatCondition` is left at the platform default:
- Default condition: "The player character has died."
- Default `text`: "Your adventure ends here. Game over."

### Continuation behavior

- **Victory automatically allows the player to continue playing.** The player is prompted; they can continue or restart.
- **Defeat does not allow continuation.** The player can only restart.

This continuation asymmetry is **hard-wired** for the top-level fields — there is no boolean to set on the top-level conditions. The asymmetry reflects the canonical "win = optional, lose = terminal" pattern. To get non-default continuation behavior (e.g., a defeat the player can continue past, or a victory that doesn't allow continuation), use System 2 instead.

### Disabling

Either field may be set to `null` to disable that ending type. The platform won't auto-fire the disabled ending — but custom trigger-based endings (System 2) still work.

### Authoring realities

**Many authors disable victory/defeat conditions entirely** because the engine's evaluation can fire too aggressively or at unintended moments. The defaults in particular have a reputation for over-firing — defeat can trigger on dark narrative content the author didn't intend as a death event.

**When you do use them, write explicit `condition` text.** Vague language causes unreliable evaluation. Common technique: use ALL CAPS for emphasis and multiple restatements.

> "ONLY trigger victory if the player has EXPLICITLY and COMPLETELY achieved escape from the island AND has been confirmed safe in the rescue boat. Do not trigger for partial success. Do not trigger for implied success."

---

## System 2: Trigger-based end-game (`effectEndsGame`)

Triggers can end the game directly via the `effectEndsGame` effect type. This is the v2.4 path for custom end conditions — multiple endings, conditional victory/defeat, or end-game logic that doesn't fit a single `condition` string.

### Basic pattern

```json
{
  "id": "Sy07xqta",
  "name": "End on Turn 5",
  "triggerConditions": [
    { "category": "condition", "type": "triggerOnTurn", "data": 5, "id": "..." }
  ],
  "triggerEffects": [
    { "type": "effectShowMessage", "data": "Time runs out!", "id": "..." },
    { "type": "effectEndsGame", "data": true, "id": "..." }
  ]
}
```

This pattern is demonstrated in the canonical fixture as the "End the Game on Turn 5" trigger.

### Continuation control

The `data` boolean on the `effectEndsGame` effect controls continuation directly:

| `data` | Behavior |
|---|---|
| `true` | Game ends; player is prompted and may choose to continue playing (victory-style). |
| `false` | Game ends; no continuation (defeat-style — restart only). |

**v2.1 consolidation note.** Pre-v2.1 worlds used a separate boolean field `canContinueEndedGame` for this control. In v2.1 that field is gone — the `data` boolean above serves both roles. The Infinite Worlds wiki currently still documents `canContinueEndedGame` as a separate field; treat that documentation as pre-v2.1 and use `effectEndsGame.data` instead.

### Don't confuse with `effectChangeVictoryCondition` / `effectChangeDefeatCondition`

Those effects **modify the engine-evaluated condition** for later evaluation (e.g., installing a new condition the engine will then evaluate true on the next turn). `effectEndsGame` **ends the game now**.

| Goal | Use |
|---|---|
| End the game right now | `effectEndsGame` |
| Change what would *cause* the game to end (engine-evaluated, fires later) | `effectChangeVictoryCondition` / `effectChangeDefeatCondition` |

---

## When to use which system

| Scenario | Use |
|---|---|
| Standard one-condition-each win/lose | Top-level `victoryCondition` / `defeatCondition` |
| Multiple ending branches | Multiple triggers with `effectEndsGame`, gated by different conditions |
| Conditional victory/defeat (depends on tracked-item state, character choice, prior triggers) | Triggers with `effectEndsGame` |
| A defeat the player can continue past, or a victory that doesn't allow continuation | Trigger with `effectEndsGame` and explicit `data: true` or `data: false` |
| Modifying win/lose mid-game without ending it now | `effectChangeVictoryCondition` / `effectChangeDefeatCondition` |

---

## Variable replacement in `text`

The `<<item_name>>` syntax works in the `text` field of both conditions. Use to reference final tracked-item values in the end-of-game message:

```
"Congratulations! You escaped with <<gold>> gold and <<companions>> companions."
```
