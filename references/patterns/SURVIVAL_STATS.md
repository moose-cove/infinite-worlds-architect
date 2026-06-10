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
