# Pattern: Target Word Count TI

> **Provenance:** KB-empirical — reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them. Apply where they fit your world's design.

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

> **Note:** Several `$name` reads in one expression do resolve: Probe F's `choose` read three tracked items in one expression (2026-09-30). What remains unconfirmed is arithmetic across several tracked items, especially with legacy bare-word names (e.g. `<<target_word_count*min_word_ratio>>`, where `min_word_ratio` is itself a TI variable). If you need two items in one formula, prefer the `$` form (`<<round($target_word_count*$min_word_ratio)>>`) and check the rendered text in World Debug.

> **Timing:** Probe F (2026-09-30) observed a `choose` expression in an extra instruction block re-render from live values each turn; see [`EXPRESSION_SWITCHED_INSTRUCTIONS.md`](EXPRESSION_SWITCHED_INSTRUCTIONS.md). If `<<…>>` math in `instructions` works the same way, as expected but not tested, a player's edit to the word count applies to the very next turn, with no trigger lag.
