# Story Extraction Tool Reference

This document covers the three MCP tools that support the sequel-world workflow: `extract_story_data`, `query_story_data`, and `get_character_list`. Use it alongside [STORY_CONTEXT_DISTRIBUTION.md](../guidance/STORY_CONTEXT_DISTRIBUTION.md) when deciding which tool to call and with which arguments.

---

## `get_character_list`

Derives a starting character list from an existing world JSON for use in `extract_story_data`. Call this on the **original world** (source), not on the sequel copy.

**Signature:**

```
get_character_list(world_path: str) -> str (JSON)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `world_path` | `str` | Absolute path to the original world JSON. |

**Returns** (JSON string):

```json
{
  "character_list": [
    {"name": "Kira", "aliases": []},
    {"name": "Lord Daro", "aliases": ["Daro", "the Lord"]}
  ],
  "source_count": 2
}
```

- `character_list` — one entry per named entity found in `possibleCharacters` and `NPCs`, in that order.
- `source_count` — number of entries returned (entries without a usable name are skipped).
- Player characters (`possibleCharacters`) have empty `aliases` (no equivalent schema field).
- NPC aliases are seeded from the world's `names` field (alternative names / short forms).

**On failure** returns `{"error": "..."}` — relative path, missing file, or invalid JSON.

**Usage pattern:**

```
1. get_character_list(world_path=<source_world_absolute_path>)
2. Present the list to the author; ask to confirm, add aliases, or augment.
3. Pass the confirmed list as character_list to extract_story_data.
```

---

## `extract_story_data`

Parses one or more IW story-export `.txt` files into structured JSON output, writing up to five files into an extraction directory.

**Signature:**

```
extract_story_data(
    input_paths: list[str],
    extraction_dir: str,
    character_list: list[dict] | None = None,
) -> str (JSON)
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `input_paths` | `list[str]` | Yes | One or more absolute paths to story-export `.txt` files. Must be non-empty. |
| `extraction_dir` | `str` | Yes | Absolute path to a directory for output files (created if absent). |
| `character_list` | `list[dict] \| None` | No | `[{"name": str, "aliases": [str]}]` for character indexing. Omit to skip `character_index.json`. |

**Returns** (JSON string) on success:

```json
{
  "totalTurns": 15,
  "turnRange": {"min": 1, "max": 15},
  "inputFilesProcessed": 1,
  "hasTrackedItems": true,
  "hasHiddenTrackedItems": false,
  "filesWritten": ["manifest.json", "metadata.json", "turn_index.json", "tracked_state.json"],
  "warnings": []
}
```

**Files written** into `extraction_dir`:

| File | Written when | Contents |
|---|---|---|
| `manifest.json` | Always | ExtractionSummary + source file provenance |
| `metadata.json` | Always | Title, story background, character (name/background/skills/starting tracked items), objective (always null) |
| `turn_index.json` | Always | Per-turn: action, outcome, secretInfo, tracked items, hidden tracked items, source file, line range |
| `tracked_state.json` | Tracked items found | Compressed snapshots: value ranges |
| `character_index.json` | `character_list` provided | Per-character: all mention locations across the export |

**On failure** returns `{"error": "..."}` — a relative path, missing input file, empty `input_paths`, or no Turn 1 in the inputs.

**Notes:**
- All paths must be absolute (the MCP server process has a different working directory from the agent session).
- Multiple `.txt` files are merged in modification-time order before parsing.
- The tool is idempotent: re-running with the same inputs overwrites the extraction directory's files atomically.

---

## `query_story_data`

Queries a directory produced by `extract_story_data` and returns the requested category as camelCase JSON.

**Signature:**

```
query_story_data(
    extraction_dir: str,
    category: str,
    turns: list[str] | None = None,
) -> str (JSON)
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `extraction_dir` | `str` | Yes | Absolute path to the extraction directory. |
| `category` | `str` | Yes | One of the six valid values (see below). |
| `turns` | `list[str] \| None` | No | Turn filter / selector. See per-category rules below. |

**Valid category values:**

| `category` | Reads from | `turns` behaviour |
|---|---|---|
| `manifest` | `manifest.json` | Ignored |
| `metadata` | `metadata.json` | Ignored |
| `turn_index` | `turn_index.json` | Filters to turns whose `number` is in the resolved list |
| `tracked_state` | `tracked_state.json` | Filters to snapshots whose `fromTurn..toTurn` range overlaps any requested turn |
| `turn_detail` | Source `.txt` files (line re-read via `turn_index.json`) | **Required**; selects which turn(s) to re-read |
| `character_index` | `character_index.json` | Ignored |

**The `turns` parameter:**

- Each element is either an int-string (`"3"`, `"15"`) or the literal `"last"`.
- `"last"` resolves to `manifest.total_turns`.
- Multiple elements are supported: `turns=["1", "5", "last"]`.
- `turn_detail` requires at least one element; other categories treat `turns=None` as "return all".

**Returns** (JSON string, camelCase): the model for the requested category:

| Category | Top-level shape |
|---|---|
| `manifest` | `{totalTurns, turnRange, inputFilesProcessed, hasTrackedItems, hasHiddenTrackedItems, filesWritten, warnings, sources}` |
| `metadata` | `{title, storyBackground, character: {name, background, skills, startingTrackedItems}, objective}` |
| `turn_index` | `{turns: [{number, action, outcome, secretInfo, trackedItems, hiddenTrackedItems, source, lineRange}]}` |
| `tracked_state` | `{snapshots: [{fromTurn, toTurn, trackedItems, hiddenTrackedItems}]}` |
| `turn_detail` | `{turnDetail: [{turn, raw, source}]}` |
| `character_index` | `{characters: {<name>: {aliases, mentions: [{turn, line, context}]}}, indexedCharacterCount, totalMentions}` |

**On failure** returns `{"error": "..."}` — a relative path, unknown category, `turn_detail` without `turns`, or a missing extraction file.

**Notes on `turn_detail`:**
- This category does NOT read from a stored file; it re-reads the raw source `.txt` lines using the `lineRange` stored in `turn_index.json`.
- The `raw` field contains the exact un-parsed text from the export file for the requested turn — use this when exact wording matters for a sequel's `firstInput` or `background`.
- The source `.txt` files must still exist on disk at the same path they were at extraction time.

---

## Usage patterns

### Minimal sequel start (no characters)

```
1. extract_story_data(input_paths=["/abs/path/export.txt"], extraction_dir="/abs/extracted/")
2. query_story_data(extraction_dir="/abs/extracted/", category="manifest")
3. query_story_data(extraction_dir="/abs/extracted/", category="metadata")
4. query_story_data(extraction_dir="/abs/extracted/", category="turn_index")
```

### Full sequel start (with character index)

```
1. get_character_list(world_path="/abs/source_world.json")
2. [Author confirms/augments character list]
3. extract_story_data(
       input_paths=["/abs/export.txt"],
       extraction_dir="/abs/extracted/",
       character_list=[{"name": "Kira", "aliases": []}, ...]
   )
4. query_story_data(category="manifest")
5. query_story_data(category="metadata")
6. query_story_data(category="turn_index")
```

### Getting the final turn's exact text

```
query_story_data(
    extraction_dir="/abs/extracted/",
    category="turn_detail",
    turns=["last"]
)
```

### Getting final tracked item values

```
# First, find last turn number from manifest
query_story_data(category="manifest")  # → totalTurns: N

# Then filter tracked_state to the last turn
query_story_data(
    extraction_dir="/abs/extracted/",
    category="tracked_state",
    turns=["last"]   # returns snapshots where fromTurn <= N <= toTurn
)
```

---

## Cross-references

- **Which field maps to which category** → [guidance/STORY_CONTEXT_DISTRIBUTION.md](../guidance/STORY_CONTEXT_DISTRIBUTION.md)
- **No-fabrication discipline** → [guidance/STORY_ACCURACY_GUARDRAILS.md](../guidance/STORY_ACCURACY_GUARDRAILS.md)
- **Citation formats** → [guidance/CITATION_METHODOLOGY.md](../guidance/CITATION_METHODOLOGY.md)
