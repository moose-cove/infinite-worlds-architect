# Field Guide: Victory and Defeat Conditions

Covers: `victoryCondition` and `defeatCondition` — each an object of shape `{condition: string, text: string, alreadyFired: boolean}`.

For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#1-top-level-fields) §1.

---

## Critical: The AI cannot see these conditions during play

> "The storyteller AI does not receive these triggers with any special context, and therefore is not influenced by their contents in any way while writing outputs."

Victory and defeat conditions are evaluated by the **platform's game engine**, not by the storyteller AI. The AI writes narrative without any awareness of these fields. This means:

- Writing "when the player defeats the villain" in `victoryCondition.condition` does **not** make the AI work toward or narrate a villain defeat.
- The conditions only end the game when the engine's evaluation determines they're met.
- The AI does not steer the story toward victory or away from defeat based on these fields.

**For AI narrative steering**, use `objective` (always-on goal) and `effectTellAIWhatToDo` trigger effects instead. The objective is what the AI optimizes for narratively; victory/defeat conditions are mechanical end-state checks.

---

## Field shape

Both `victoryCondition` and `defeatCondition` are objects, not strings:

```json
{
  "condition": "The player has escaped the island.",
  "text": "Congratulations! You have been successful in your adventure.",
  "alreadyFired": false
}
```

| Sub-field | Type | Notes |
|---|---|---|
| `condition` | string | Free-form English expression the engine evaluates each turn. |
| `text` | string | Message shown to the player when the condition fires. |
| `alreadyFired` | boolean | Platform runtime state. **Never write `true` from the plugin** — this is a runtime flag the platform sets when the condition has already triggered. |

Either field may be `null` if the world has no configured victory/defeat (some worlds disable the system entirely and rely on triggers).

---

## Defaults

If `victoryCondition` is left at the platform default (with empty `condition`):

- Default condition: "The player character has succeeded in their initial goals" (contextualized by the platform at runtime).
- Default `text`: "Congratulations! You have been successful in your adventure."

If `defeatCondition` is left at the platform default (with empty `condition`):

- Default condition: "The player character has died."
- Default `text`: "Your adventure ends here. Game over."

---

## Authoring realities

**Many authors disable victory/defeat conditions entirely** because the engine's evaluation can fire too aggressively or at unintended moments. The defaults in particular have a reputation for over-firing — defeat can trigger on dark narrative content the author didn't intend as a death event.

**When you do use them, write explicit `condition` text.** Vague language causes unreliable evaluation. Common technique: use ALL CAPS for emphasis and multiple restatements.

> "ONLY trigger victory if the player has EXPLICITLY and COMPLETELY achieved escape from the island AND has been confirmed safe in the rescue boat. Do not trigger for partial success. Do not trigger for implied success."

**For precise victory/defeat control, modify conditions via triggers.** Use `effectChangeVictoryCondition` and `effectChangeDefeatCondition` to swap the active conditions at story phase transitions. Both effects take a `{condition, text, alreadyFired}` object as their data.

This pattern is the v2.1-canonical alternative to ending the game from inside a trigger:

1. Start the world with permissive or null `victoryCondition`/`defeatCondition`.
2. At the appropriate plot phase, fire a trigger that uses `effectChangeVictoryCondition` to install a condition the engine will then evaluate true on the next turn.
3. The engine evaluates, the condition fires, the game ends.

---

## Variable replacement in `text`

The `<<item_name>>` syntax works in the `text` field of both conditions. Use to reference final tracked-item values in the end-of-game message:

```
"Congratulations! You escaped with <<gold>> gold and <<companions>> companions."
```

---

## When to use vs. disable

**Use the fields when:**
- The world has a single, simple, clearly-stated win/lose condition.
- You're comfortable with the engine's interpretation latitude.
- Example: `"The player has escaped the island"` / `"The player has been captured"`.

**Disable (set to `null`) and rely on triggers when:**
- The world has complex, multi-stage end conditions.
- You need precise control over end timing.
- The default conditions fire incorrectly during playtesting.
- The world's "ending" is multi-branching (different effects per branch) — use `effectChangeVictoryCondition`/`effectChangeDefeatCondition` triggers to install the right ending for each branch.
