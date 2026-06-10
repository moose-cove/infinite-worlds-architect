# World Design Patterns

> **Provenance:** KB-empirical — reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them. Apply where they fit your world's design.

Recurring architectural patterns from real IW world builds. Each pattern can be applied independently; they compose without conflict.

---

## Pattern 1 — Phase Escalation via EIB Replacement

Use an `instructionBlock` (EIB) as a **mutable world-state container**. The EIB starts with phase-1 content; triggers fire at key story beats and use `effectModifyInstructionBlock` to replace the entire EIB content with the next phase. Each phase can describe different world conditions, faction states, NPC behaviours, or stakes.

**Why EIB replacement beats `effectChangeMainInstructions`:** EIBs are modular — one EIB handles phase-sensitive world state; others handle tone, character, or style that don't change. `effectChangeMainInstructions` is all-or-nothing; EIBs let you surgically swap only the evolving part. EIBs are also easier to manage in the world editor since each has a focused purpose.

**Pattern template:**

```json
{
  "id": "EibPhase1",
  "name": "World State",
  "content": "PHASE 1: [Describe conditions, faction states, environmental context for phase 1...]"
}
```

At the escalation trigger:

```json
{
  "id": "uuid",
  "type": "effectModifyInstructionBlock",
  "data": {
    "id": "EibPhase1",
    "content": "PHASE 2: [Describe escalated conditions...]"
  }
}
```

**Chaining phases:** Use `triggerPrereqs` on the Phase 3 trigger (require Phase 2 to have fired) to ensure the escalation chain fires in order even if timing conditions overlap.

**Naming convention:** Give the phase EIB a stable ID (e.g. `EibPhase1`) and a descriptive name (e.g. `"World State"`). Use `effectModifyInstructionBlock` to replace only its `content` — the `id` and `name` remain constant across all phases.

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

## Pattern 3 — Target Word Count TI Pattern

A player-adjustable `number` TI that controls turn length. The TI is visible to everyone and is not auto-updated — the player edits it directly in Storyteller Mode. Its variable is then used in `instructions` or `descriptionRequest` with IW's `<<>>` math expressions.

**TI definition:**

```json
{
  "id": "TgtWrdCnt",
  "name": "Target Word Count",
  "dataType": "number",
  "visibility": "everyone",
  "autoUpdate": false,
  "updateInstructions": "",
  "initialValue": "500",
  "description": "Controls the length of each turn's narrative. Player can adjust this value. The storyteller AI will target this word count with a ±20% range."
}
```

**Basic use in `instructions`:**

```
The length of outcomeDescription must always be between <<round(target_word_count*0.8)>> and <<round(target_word_count*1.2)>> words.
```

**Full instruction block with paragraph control:**

```
Critically and extremely important, overriding any previous or future instructions:
outcomeDescription must be a minimum of <<round(target_word_count*0.8)>> words and
<<round(target_word_count/50)>> paragraphs and a maximum of <<round(target_word_count*1.2)>>
words and <<round(target_word_count/40)>> paragraphs. Never summarize or be concise —
show don't tell. Extend scenes and expand connecting scenes if needed.
```

**Ratio reference (initial value 500):**

| Formula | Result at 500 | Result at 2000 |
|---|---|---|
| `*0.8` min words | 400 | 1600 |
| `*1.2` max words | 600 | 2400 |
| `/50` min paragraphs | 10 | 40 |
| `/40` max paragraphs | 12 | 50 |

> **Note:** Multi-variable equations (e.g. `<<target_word_count*min_word_ratio>>` where `min_word_ratio` is itself a TI variable) are not confirmed to work — don't chain TI references inside math expressions.

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
