# Story Extraction Strategy

A guide for **any** plugin agent that needs to read a played Infinite Worlds story — not only the `sequel-world` command. For example, a `modify-world` agent can extract a story export to check how a world change actually played out, or to ground a revision in what happened during a session.

The `extract_story_data`, `query_story_data`, and `get_character_list` MCP tools are **self-describing** — call them and read their tool descriptions for signatures, parameters, and return shapes. This document covers what the per-tool docstrings structurally cannot: **cross-call strategy** — which categories to load, in what order, and how to budget the expensive ones.

---

## 1. Extraction output files

`extract_story_data` writes up to five JSON files into the extraction directory; `query_story_data` reads them back by `category`:

| File | Category | Always written | Contents |
|---|---|---|---|
| `manifest.json` | `manifest` | Yes | Turn count, turn range, source files, warnings |
| `metadata.json` | `metadata` | Yes | Title, story background, character (name/background/skills/starting tracked items). `objective` is always null — see the note below. |
| `turn_index.json` | `turn_index` | Yes | Per-turn action, outcome, secret info, tracked-item state, hidden tracked-item state, source file, line range |
| `tracked_state.json` | `tracked_state` | If tracked items exist | Compressed snapshots: turn ranges over which tracked-item state held constant |
| `character_index.json` | `character_index` | If a character list was provided | Per-character mention list (turn, line, context) across the export |

> **`metadata.objective` is always null.** IW story exports have no Objective section, so the header parser never populates it — this is a property of the export *format*, not of any particular world. An agent that needs a world's objective should read it from the world JSON, not the extract.

---

## 2. Tiered loading sequence

Load cheapest-first; stop at the tier that answers your question.

### Tier 1 — load first (one call each, all small)

- `query_story_data(category="manifest")` — turn count/range, file list, warnings.
- `query_story_data(category="metadata")` — title, background, character.
- `query_story_data(category="turn_index")` — every turn's action / outcome / secretInfo / tracked-item state in lightweight form.

These three fit in context and answer most questions on their own.

### Tier 2 — load on demand

- `query_story_data(category="tracked_state")` — when you need final tracked-item values or how they evolved over play.
- `query_story_data(category="character_index")` — when mapping a character's mentions/interactions (requires a character list at extraction time).

### Tier 3 — targeted, budgeted (3–7 calls per session)

- `query_story_data(category="turn_detail", turns=["N"])` / `turns=["last"]` — re-reads the **raw** source lines for a turn when exact wording matters (the `turn_index` stores summaries). `"last"` resolves to `manifest.totalTurns`.

**Budget: 3–7 `turn_detail` calls.** Use `turn_index` to pick the few turns that matter (pivotal events, reveals, final states); don't slurp every turn. `turn_detail` re-reads the original `.txt` files, so they must still exist at their extraction-time paths.

---

## 3. Keep always-on context lean

Load Tier 1 at the start; pull Tier 2/3 only when a specific question needs them. The `turn_index` already carries per-turn `action`, `outcome`, `secretInfo`, and tracked-item state, so most reads don't need `turn_detail` at all — reserve it for cases where exact wording matters (e.g., lifting a precise line for a quote or an opening premise).

---

## Cross-references

- **Tool signatures / parameters / returns** → the tools' own descriptions (self-describing; no separate reference).
- **Building a sequel world from a story** (field-to-source mapping, citation and no-fabrication discipline) → the `/infinite-worlds-architect:sequel-world` command, which carries that discipline inline.
