# Story Export Extraction Guide

A guide for **any** plugin agent that needs to read a played Infinite Worlds story — not only the `sequel-world` command. For example, a `modify-world` agent can extract a story export to check how a world change actually played out, or to ground a revision in what happened during a session.

The `extract_story_data`, `query_story_data`, `search_turns`, and `get_character_list` MCP tools are **self-describing** — call them and read their tool descriptions for signatures, parameters, and return shapes. This document covers what the per-tool docstrings structurally cannot: **cross-call strategy** — which categories to load, in what order, and how to budget the expensive ones.

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

### Tracked items: pass the world's item names

When you have the world that produced the story, pass every one of its `trackedItems[*].name` (hidden items included) as `extract_story_data(tracked_item_names=[...])`, copied verbatim — a trailing space is part of the name (`"Exp "` appears in the export as `Exp :`). The same names are used for the header's Starting Tracked Items. The export writes each tracked item as a `Name:` line followed by its value. A YAML-typed item's value often has its own lines ending in `:`, such as map keys (`Shapeshift:`) or `- |-` block content.

Every rule requires an item's name line to open the section or follow a blank line. IW separates items with one blank line, and an empty item is a name line followed by two blank lines.
- **With names**, a name line must also match a listed name exactly. A listed name that appears inside a value (no blank line before it) stays in that value.
- **Above the first listed item, the no-names rule applies.** A column-0 `Key:` line at a boundary becomes its own unlisted item. Any other non-blank text there belongs to no item and is dropped, and the manifest says so.
- **If no listed name opens an item in a section**, that section uses the no-names rule.
- **Without names**, a name line must start at column 0. This rule held on every turn of a 53-turn YAML-heavy export.
- **It fails when a value itself contains a blank line followed by a column-0 `Something:` line**, as a YAML block scalar with blank lines would.
- **Items that are not separated by blank lines are merged in either mode.**

Values are always raw strings. The extractor never parses or validates the YAML, because AI-written YAML is often invalid. `manifest.warnings` flags suspected mis-splits.
- **With names**, each warning names the line and its turns and says what happened to it:
  - an unlisted name line was kept inside the listed item above it;
  - an unlisted line above the first listed item was kept as its own item;
  - no listed name matched in the section, so the blank-line rule was used;
  - a listed name line that isn't at a boundary was kept inside a value;
  - a listed name never appeared;
  - non-blank lines above the first item could not be assigned to any item and were dropped (this one also appears without names).
- **Without names**, it flags a tracked-item key set that changes from one turn to the next. Items normally appear on every turn, so a change usually means a split.
- **Also without names**, one summary warning counts the column-0 `Key:` lines kept inside values. This fires on any YAML-map world. It is a prompt to pass `tracked_item_names`, not proof of an error.
- **Not every mis-split is reported.** Without names, a blank line followed by a column-0 `Key:` that splits a value is visible only if the key set changes between turns. With names, items that are not separated by blank lines are flagged only when the merged line is itself a listed name: `Gold:\n5\nJunk:\n1` with names `["Gold"]` merges silently.
- **The header's Starting Tracked Items get the same name-based warnings**, worded "(the header)" instead of a turn list. The without-names summary counts and key-set checks cover turns only.

> **`metadata.objective` is always null.** IW story exports have no Objective section, so the header parser never populates it — this is a property of the export *format*, not of any particular world. An agent that needs a world's objective should read it from the world JSON, not the extract.

---

## 2. Tiered loading sequence

Load cheapest-first; stop at the tier that answers your question.

### Tier 1 — load first (one call each, all small)

- `query_story_data(category="manifest")` — turn count/range, file list, warnings.
- `query_story_data(category="metadata")` — title, background, character.
- `query_story_data(category="turn_index")` — every turn's full action / outcome / secretInfo text (whitespace-trimmed) plus tracked-item state. Pass `turns=[...]` to fetch only specific turns.

These three fit in context and answer most questions on their own.

### Tier 2 — load on demand

- `query_story_data(category="tracked_state")` — when you need final tracked-item values or how they evolved over play. Pass `items=["Level", "Exp"]` to return only those items (exact match first, then case-insensitive with surrounding whitespace ignored, so `"Exp"` finds `"Exp "`; an unknown name errors and lists the available ones). Add `changes_only=True` to merge adjacent snapshots whose selected values are equal, giving one entry per run of unchanged values: the turns where any of those items changed. `items` also works on `turn_index`. If any item changes every turn (a story log, say), every snapshot is one turn wide, so `items` + `changes_only` is the cheap way to follow one or two items across a long story.
- `query_story_data(category="character_index")` — when mapping a character's mentions/interactions (requires a character list at extraction time).
- `search_turns(query=...)` — when you need the turns that mention a thing (an object, a place, a phrase, a regex). Returns matching turn numbers with per-section match counts, and optional context snippets. Searches `action` / `outcome` / `secretInfo` only; follow tracked items with `tracked_state`.

**Find with `search_turns`, read with `query_story_data`.** To locate turns by content, use `search_turns` — not `grep` over the export files. To read the turns it found, pass their numbers to `query_story_data(category="turn_index", turns=[...])`, which returns the full section text at no budget cost; spend a `turn_detail` call only when you need the raw exported lines (Tier 3). Never `Read` or `sed` the `.txt` with line numbers you worked out yourself: when several exports overlap, the extraction keeps the copy of each turn from the newest file, and a hand-computed slice can land on a superseded copy in an older one. Snippets from `search_turns` locate evidence — read the turn before quoting or citing it, since a snippet is cut at the edges and can drop a qualifier just outside its window.

### Tier 3 — targeted, budgeted (3–7 calls per session)

- `query_story_data(category="turn_detail", turns=["N"])` / `turns=["last"]` — re-reads the **raw** source lines for a turn when you need it exactly as exported — section headers, tracked-item blocks and layout intact. (`turn_index` already has each section's full text, so you don't need `turn_detail` just to see what a turn said.) `"last"` resolves to `manifest.totalTurns`.

**Budget: 3–7 `turn_detail` calls.** Use `turn_index` (or `search_turns`, when you know what you're looking for) to pick the few turns that matter (pivotal events, reveals, final states); don't slurp every turn. `turn_detail` re-reads the original `.txt` files, so they must still exist at their extraction-time paths.

---

## 3. Keep always-on context lean

Load Tier 1 at the start; pull Tier 2/3 only when a specific question needs them. The `turn_index` already carries per-turn `action`, `outcome`, `secretInfo`, and tracked-item state, so most reads don't need `turn_detail` at all — reserve it for cases where you need the turn exactly as exported.

---

## Cross-references

- **Tool signatures / parameters / returns** → the tools' own descriptions (self-describing; no separate reference).
- **Building a sequel world from a story** (field-to-source mapping, citation and no-fabrication discipline) → the `/infinite-worlds-architect:sequel-world` command, which carries that discipline inline.
