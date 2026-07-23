# Pattern: Survival Stats Single-TI

> **Provenance:** KB-empirical — reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them. Apply where they fit your world's design.

---

## Pattern 2 — Survival Stats Single-TI Pattern

A single `text` TI with detailed numerical update rules per stat. The AI updates all stats in one TI following the rules each turn.

**Why one TI instead of separate number TIs:** Holistic tracking is easier for the AI — it can apply inter-stat interactions (e.g. cold environment + insulating clothing = no Temperature decrease) without having to reason across disconnected items.

Example stat set: Hunger, Thirst, Sleep, Body Temperature, Stamina. Each stat entry specifies:
- Decrease rules (time-based + activity-based, specific numbers)
- Increase rules (consuming items, resting, specific numbers)
- Hard limits (never exceed 100, never below 0)
- Special interactions between stats

**Key design notes:**
- Include specific numbers (not vague descriptions) in `updateInstructions` so the AI makes consistent mechanical decisions
- Set `autoUpdate: true` so the AI updates every turn without prompting
- Set `visibility: "ai_only"` if you don't want stat values cluttering the player's UI

**Minimal TI structure:**

```json
{
  "id": "SrvStats",
  "name": "Survival Stats",
  "dataType": "text",
  "visibility": "ai_only",
  "autoUpdate": true,
  "updateInstructions": "Update on every turn. Stats: Hunger (decreases 5/turn, +30 from meal, max 100, min 0), Thirst (decreases 8/turn, +40 from drink, max 100, min 0). Never exceed 100 or go below 0.",
  "initialValue": "Hunger: 80\nThirst: 80"
}
```

---

### v2.2 note — deterministic version with YAML + `effectRunScript`

The text-TI version above works, but the arithmetic is done by the AI
every turn: it reads the current numbers out of freeform text, applies the
decrease/increase rules itself, and re-writes the text. That's exactly the
kind of mechanical bookkeeping the AI is prone to getting wrong under
context pressure (drift, off-by-one accumulation, forgetting a rule for
one stat but not another).

As of v2.2, prefer a `yaml` tracked item holding the stats as structured
fields, mutated by an `effectRunScript` trigger instead of AI narration:

```json
{
  "id": "SrvStats",
  "name": "Survival Stats",
  "dataType": "yaml",
  "variableName": "survival_stats",
  "visibility": "ai_only",
  "autoUpdate": false,
  "initialValue": "hunger: 80\nthirst: 80"
}
```

Trigger (fires every turn — `canTriggerMoreThanOnce: true`, no conditions
needed beyond that):

```
$survival_stats.hunger -= 5
if $survival_stats.hunger < 0:
  $survival_stats.hunger = 0
$survival_stats.thirst -= 8
if $survival_stats.thirst < 0:
  $survival_stats.thirst = 0
```

Meal/drink consumption still fires its own trigger (e.g. on
`triggerOnEvent: "the player eats"`) with a script that does
`$survival_stats.hunger += 30` and clamps to 100 the same way.

**Why this is better:** the decrease/increase math and the clamping rules
are now guaranteed correct every single turn — no AI arithmetic, no drift,
no need to spell out "never exceed 100 or go below 0" as a hope-it-follows
instruction. `updateInstructions` disappears entirely for this TI; `autoUpdate`
turns off because the trigger does the mutation, not the AI.

**When the text-TI version still makes sense:** stats with genuinely
holistic, narrative-dependent interactions (e.g. "cold environment +
insulating clothing = no Temperature decrease") that require the AI to
read the current scene and decide whether a rule applies. Pure numeric
decay/refill on fixed schedules is the case to migrate; conditional,
scene-dependent interactions between stats still need the AI's judgment
and are better left as `updateInstructions` text (or a hybrid: numeric
stats on the YAML TI, with an `effectTellAIWhatToDo` effect providing the
scene-dependent override on the turns it applies).
