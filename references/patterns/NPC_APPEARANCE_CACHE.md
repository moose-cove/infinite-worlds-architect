# Pattern: NPC Appearance Cache TI

> **Provenance:** KB-empirical — reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them. Apply where they fit your world's design.

---

## Pattern 4 — NPC Appearance Cache TI

An `ai_only` `text` TI that the AI maintains as a rolling cache of recently-seen NPC appearances. Keeps image generation consistent for recurring NPCs without relying on context window memory (which degrades over long games).

**TI definition:**

```json
{
  "id": "AppCache",
  "name": "Appearance tracking",
  "dataType": "text",
  "visibility": "ai_only",
  "autoUpdate": true,
  "updateInstructions": "Add or update entries for all NPCs met this turn. Remove NPCs not mentioned in the last 7 turns. MAX 100 words total. Per NPC: age, ethnicity, height, build, hair, eyes, notable features only.",
  "initialValue": ""
}
```

The AI reads this cache when populating `illustrAppearance` and `illustrClothes` fields, giving the image model consistent per-character descriptions across turns.

**When to use:** Any world with recurring named NPCs where you care about consistent visual output. Cost is low (one small `ai_only` TI); benefit is substantial for image-heavy worlds.
