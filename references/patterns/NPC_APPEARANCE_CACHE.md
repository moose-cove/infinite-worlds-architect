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

---

### v2.2 note — partial migration, judgment call

The *content* of this cache (deciding which NPCs appeared this turn, and
writing their appearance descriptions) is inherently AI judgment —
`effectRunScript` can't read the narrative and can't generate prose, so it
can't take over the core job of this pattern. Structuring the cache as a
`yaml` tracked item (one list entry per NPC: `id`, `description`,
`lastSeenTurn`) is possible, but the AI would still write the descriptive
fields itself via `updateInstructions`/`autoUpdate` exactly as today —
YAML buys clearer structure, not less AI work.

The one piece that genuinely is mechanical bookkeeping is the "remove
NPCs not mentioned in the last 7 turns" clause — that's pure turn-count
arithmetic once you know which NPCs were touched this turn. If you adopt
the YAML structure above, an `effectRunScript` trigger firing every turn
can increment each entry's `lastSeenTurn` gap and prune entries past the
threshold deterministically, leaving the AI responsible only for adding/
updating entries it actually observed — not for correctly counting turns
across a long game. This is optional: the plain-text version above is
simpler to author and adequate for shorter games or worlds with few
recurring NPCs.
