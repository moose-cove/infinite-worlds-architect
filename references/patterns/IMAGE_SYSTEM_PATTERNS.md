# Image System Design Patterns

> **Provenance:** KB-empirical — reverse-engineered from community image EIBs tested against Manticore (IW's image model) and real world builds (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them.
>
> **Scope:** These are generic, world-neutral patterns for consistent image output. The NSFW-specific "BSS" / "ASS" adult-content template frameworks are **not documented here** — they are out of scope for this plugin's shipped reference set. The generic mechanics documented below (persistent attribute storage, exact-string tables, multi-pass validation, field isolation) are the portable, world-neutral core of those systems.

Consistent image generation in IW requires disciplined prompt engineering inside the EIB that controls the `illustr*` fields. These four patterns compose: you can apply any subset independently or stack all four for the strictest consistency.

---

## Pattern 1 — Persistent Attribute Storage in `illustrClothesChanged`

> **Note on `illustrClothesChanged`:** This is a per-turn **runtime** field the storyteller AI emits each turn — it is **not** part of the authoring schema or fixture (the only image fields the schema/fixture define are the seven `imagePromptDetails` members: `illustrGenre`, `illustrClothes`, `illustrSetting`, `illustrSubject`, `illustrAppearance`, `illustrIsCharacter`, `illustrExpressionPosition`). The persistence behavior described below is KB-empirical and **cannot be verified from the schema or fixture**; confirm against live runtime output before relying on it.

`illustrClothesChanged` is written every turn for all characters. This makes it a reliable vehicle for carrying persistent per-character state across turns without a separate TI.

**Mechanism:** Extend the field value from a plain boolean to include keyed attribute data:

```
illustrClothesChanged: (<character_id>): [TRUE/FALSE, attr:VALUE]
```

On each turn, the AI extracts `attr:VALUE` from the previous turn's `illustrClothesChanged` to recover the current attribute state.

**Why it works:** The field is always written, so the value never gets lost between turns — unlike `secretInfo` (which is AI-generated and may drift) or a TI that the AI updates inconsistently.

**Generalizable to any per-character attribute:** The pattern works for transformation stage, clothing tier, injury level, corruption level, or any other per-character value that must persist exactly across turns.

**EIB persistence rules to add:**

```
ATTRIBUTE PERSISTENCE: Extract [attr:VALUE] from illustrClothesChanged each turn.
- If no [attr:X] found in previous turn's data: use fallback default (world-specific).
- Attribute CANNOT CHANGE unless an explicit in-world event occurs.
- Pre-output: verify current attr matches the value in illustrClothesChanged. If mismatch: revert and log.
```

---

## Pattern 2 — Exact String Tables for Consistent Attribute Descriptions

Instead of letting the AI rephrase attribute descriptions each turn (which causes gradual drift), define exact copy-paste strings for each attribute value. The AI must use these verbatim.

**Table structure (add to your image EIB):**

```
| Attribute Value | illustrClothes string            | illustrExpressionPosition string |
|-----------------|----------------------------------|----------------------------------|
| VALUE_1         | "exact string for VALUE_1"       | "exact string for VALUE_1"       |
| VALUE_2         | "exact string for VALUE_2"       | "exact string for VALUE_2"       |
```

**Enforcement rules:**

```
Exact Strings: ALWAYS copy-paste from the table. NEVER rephrase or synonym-replace.
Forbidden Words: [list words that ONLY appear in exact strings and must not appear elsewhere]
If either field lacks the exact string → replace with exact string from table.
```

**Why this matters:** Rephrasing the same attribute differently each turn sends contradictory signals to the image model, causing visual inconsistency. Exact strings give the image model a stable anchor.

---

## Pattern 3 — Multi-Pass Output Validation

Add a pre-output validation sequence to your image EIB. The AI checks its own output before writing it, catching errors before they reach the image model.

**Validation pipeline template:**

```
PRE-OUTPUT VALIDATION:
Step 0 — HARD BLOCK CHECK:
  Scan illustrAppearance for: [list prohibited terms]
  If found → STOP. Do not generate output. Remove term and regenerate.

Step 1 — Field isolation check:
  [AttributeTerms] ONLY in [allowedFields]. If found elsewhere → remove + log.

Step 2 — Exact string verification (if using Pattern 2):
  Verify exact strings present in required fields. If absent or mismatched → replace.

Step 3 — Action verb check:
  illustrClothes must not contain action verbs. If found → remove.

Logging format: // [CHECK]: [finding] → [action taken]
```

**Why this matters:** The image model receives cleaner, more consistent prompts. The AI's self-correction catches the most common generation errors (leaked prohibited terms, missing required strings, wrong field content) before they compound across turns.

---

## Pattern 4 — Field Isolation Rules

Define which types of descriptions belong in which fields, with absolute prohibitions. This prevents the image model from receiving duplicate or contradictory signals.

**Standard field isolation:**

| Field | Allowed content | Prohibited |
|---|---|---|
| `illustrAppearance` | Observable, factual physical traits only (age, ethnicity, build, hair, eye color, skin tone, notable features) | Subjective adjectives, occupations, moods, value judgments, persistent attribute descriptions |
| `illustrClothes` | Clothing only (garments, fabric, material, fit) + any persistent attribute strings (Pattern 2) | Action verbs, appearance traits, expressions |
| `illustrExpressionPosition` | Pose, emotion, action, temporary effects, Director Info camera/lens block | Persistent appearance traits (except attribute strings assigned here by Pattern 2) |
| `illustrSetting` | Environment only (background, mid-ground, foreground layers) | Characters, subjects, NPCs |

**Enforcement rule to add to your EIB:**

```
FIELD ISOLATION: Each field type is strictly bounded. Content that belongs in one field
must NEVER appear in another. illustrAppearance: physical traits only. illustrClothes:
garments only (+ attribute strings). illustrExpressionPosition: pose/emotion/action only.
illustrSetting: environment only, NO characters.
```

---

## Combining the Patterns

These four patterns compose additively:

| What you want | Apply |
|---|---|
| Basic structure and word limits | See `IMAGE_STYLE.md` (Xyphrax Director or Thyr templates) |
| Consistent appearance for recurring characters | Add Pattern 1 (persistent storage) |
| Eliminate description drift over many turns | Add Pattern 2 (exact string tables) |
| Catch generation errors before they compound | Add Pattern 3 (multi-pass validation) |
| Prevent contradictory signals to the image model | Add Pattern 4 (field isolation) |
| Maximum consistency (transformation or complex worlds) | All four patterns together |

For standard worlds, Patterns 3 + 4 alone provide meaningful consistency improvement with modest EIB length increase.
