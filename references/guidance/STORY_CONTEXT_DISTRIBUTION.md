# Story Context Distribution

This document maps sequel world fields to their story-extraction data sources and specifies the tiered loading sequence. Use it to decide which `query_story_data` call to make for each field, and to keep always-on context lean.

---

## 1. Extraction output files

`extract_story_data` writes up to five files into the extraction directory. Each file is a JSON document readable via `query_story_data`:

| File | Category key | Always written | Contents |
|---|---|---|---|
| `manifest.json` | `manifest` | Yes | Turn count, turn range, source files, warnings |
| `metadata.json` | `metadata` | Yes | Title, story background, character (name, background, skills, starting tracked items), objective (always null in exports) |
| `turn_index.json` | `turn_index` | Yes | Per-turn: action text, outcome text, secret info, tracked item state, hidden tracked item state, source file, line range |
| `tracked_state.json` | `tracked_state` | If tracked items exist | Compressed snapshots: value ranges where tracked items held a constant state |
| `character_index.json` | `character_index` | If character list provided | Per-character: all mentions (turn, line number, context line) across the full export |

---

## 2. Tiered loading sequence

Load data in this order, from cheapest to most expensive. Stop loading a given tier when you have enough information for the field in question.

### Tier 1 — Always load first (single call each)

| Call | Data returned | Cost |
|---|---|---|
| `query_story_data(category="manifest")` | Total turns, turn range, file list, warnings | Tiny |
| `query_story_data(category="metadata")` | Title, background, character, objective | Tiny |
| `query_story_data(category="turn_index")` | All turns, lightweight (action/outcome/secret_info/TI state per turn) | Small–medium |

Load all three of these before starting field proposals. They fit in context and provide the bulk of sequel-world evidence.

### Tier 2 — Load on demand

| Call | When to use | Cost |
|---|---|---|
| `query_story_data(category="tracked_state")` | When the sequel needs to know final tracked item values or how values evolved over play | Medium |
| `query_story_data(category="character_index")` | When building character mentions and interaction maps for a character-heavy sequel | Medium |

### Tier 3 — Targeted queries only (budget: 3–7 calls)

| Call | When to use | Cost |
|---|---|---|
| `query_story_data(category="turn_detail", turns=["N"])` | When a specific turn outcome, secret_info, or action text needs exact wording (the turn_index stores summaries; turn_detail re-reads raw source lines) | Per-turn |
| `query_story_data(category="turn_detail", turns=["last"])` | When the final story state is needed for the sequel's opening premise | Per-turn |

**Budget guideline: 3–7 `turn_detail` queries per session.** Do not slurp every turn. Use the `turn_index` to identify the 3–7 most relevant turns (pivotal events, character reveals, final tracked item states) and query those. Querying all turns wastes context and produces noise.

The `"last"` keyword resolves to `manifest.total_turns` and is useful for grabbing the final turn without knowing the exact turn number in advance.

---

## 3. Field-to-source mapping

| Sequel world field | Primary source | Category | Notes |
|---|---|---|---|
| `title` | `metadata.title` | `metadata` | Often the world's original title; may need sequel suffix. |
| `description` | `metadata.story_background` | `metadata` | Story background text. |
| `background` | `metadata.story_background` + relevant turn outcomes | `metadata`, `turn_detail` | Background is the scene-setter; blend world background with how the story ended. |
| `instructions` | Original world (carry forward) | — | Carry forward; story export doesn't contain instruction text. |
| `authorStyle` | Original world (carry forward) | — | Carry forward. |
| `firstInput` | Last turn outcome / author direction | `turn_detail` (turns=["last"]) | The sequel's opening premise; the last turn is the best anchor. |
| `objective` | **No story-export source — see below** | — | Must be `CARRY_FORWARD:` or `USER_DIRECTED:`. |
| `possibleCharacters[*].name` | `metadata.character.name` | `metadata` | Protagonist name from the played session. |
| `possibleCharacters[*].description` | Original world + author direction | — | Story export doesn't contain character descriptions. |
| `possibleCharacters[*].skills` | `metadata.character.skills` | `metadata` | Skill list from the session header. **Type mismatch:** `metadata.character.skills` is a raw `str \| None` (the header line as written); the world `skills` field is a `{skill: value}` object. Do not copy directly — parse the string and map to the world's existing `skills` keys. |
| `trackedItems[*]` (final values) | `tracked_state` (last snapshot) | `tracked_state` | Use snapshots where `toTurn == manifest.total_turns`. |
| `trackedItems[*]` (labels/instructions) | Original world (carry forward) | — | Tracked item structure doesn't appear in exports. |
| `NPCs[*].detail` | `character_index` + `turn_detail` | `character_index`, `turn_detail` | What the story actually showed about each NPC. Use carry-forward for anything not shown. |
| `NPCs[*].secret_info` | `turn_index` / `turn_detail` (secret info sections) | `turn_index`, `turn_detail` | Secret info per-turn; only update what the export revealed. |
| `triggerEvents` | Original world (carry forward) | — | Story export contains no trigger data; carry forward and adapt as needed. |
| `instructionBlocks` | Original world (carry forward) | — | Carry forward. |
| `loreBookEntries` | Original world + author direction | — | Carry forward; update if story revealed new lore. |
| `imageStyle*` / `illustrationStyle*` | Original world (carry forward) | — | Story export contains no image settings. |

---

## 4. The `objective` field — no story-export source

There is no Objective section in IW story exports. The export format does not carry the world's `objective` field, and no story turn section provides an equivalent. The `metadata.objective` field in the extraction is always `null`.

**Rule:** The sequel's `objective` must always be cited as:
- `CARRY_FORWARD: <reason>` — the original world's objective still applies, or
- `USER_DIRECTED: <reason>` — the author has specified a new objective for the sequel.

Never cite a turn or Story Metadata for `objective`. The citation gate will not block `CARRY_FORWARD:` or `USER_DIRECTED:` citations for this field; it will block any attempt to cite a non-existent story source.

---

## 5. Always-on vs. on-demand context

Keep the always-on context lean:
- Load `manifest`, `metadata`, and `turn_index` at the start of every sequel-world session (Tier 1).
- Do not pre-load `tracked_state`, `character_index`, or `turn_detail` unless the world has tracked items or significant NPC coverage in the story export.

The `turn_index` already contains per-turn `action`, `outcome`, `secretInfo`, and tracked item state. For most fields, this is sufficient without querying `turn_detail`. Reserve `turn_detail` (raw line re-reads) for cases where the exact wording matters — e.g., crafting the sequel's opening `firstInput` from the last turn's precise outcome text.

---

## Cross-references

- **Citation formats** → [CITATION_METHODOLOGY.md](./CITATION_METHODOLOGY.md)
- **No-fabrication discipline** → [STORY_ACCURACY_GUARDRAILS.md](./STORY_ACCURACY_GUARDRAILS.md)
- **Tool signatures and output file formats** → [mechanics/STORY_EXTRACTION_TOOL.md](../mechanics/STORY_EXTRACTION_TOOL.md)
- **Field authoring judgment** → matching file in `references/fields/`
