# iw_architect.story

A deterministic, no-LLM parser that turns Infinite Worlds **story exports** (played-session
transcripts) into structured JSON for building "sequel" worlds.

## Purpose

Story exports are plain-text files produced when a player exports an Infinite Worlds session.
This package reads one or more of those files, merges them when they overlap (e.g. re-exports
of an ongoing session), and emits a directory of structured JSON files that a sequel-world
builder can query to carry forward state, character arcs, and narrative outcomes.

No language model is invoked anywhere in this package. Every operation is pure Python parsing
and file I/O. The MCP wrappers that surface these functions as tools are added in PR2.

## Modules

| Module | Role |
|---|---|
| `combine` | Reads and merges one or more export `.txt` files into a single `CombineResult`, resolving duplicate turns by file mtime (newest wins) and flagging gaps in the turn sequence. |
| `header` | Parses the preamble section of an export (world title, story background, starting character, starting tracked items) into a `HeaderData` dict. |
| `sections` | Splits a single turn body into its named sections (Action, Outcome, Secret Information, Tracked Items, Hidden Tracked Items) and returns a `TurnSections` model with raw section text. |
| `tracked` | Parses a tracked-items section body into `{key: value}` dicts (`parse_tracked_items`) and computes a snapshot-on-change list over all turns (`generate_snapshots`), returning `Snapshot` models. |
| `extract` | Orchestrates the full pipeline: combine → parse header → parse turns → build snapshots → index characters → write JSON files. Returns an `ExtractionSummary` model. |
| `characters` | Scans each turn's source lines for word-boundary matches of character names and aliases, returning a `CharacterIndex` model. |
| `query` | Reads the JSON files written by `extract` and returns typed models for each category: `manifest`, `metadata`, `turn_index`, `tracked_state`, `character_index`, `turn_detail`. |
| `models` | Pydantic v2 model definitions for all pipeline inputs and outputs. |

## Casing convention

Python attributes use **snake_case**; serialised JSON object keys use **camelCase**.

This is achieved via `pydantic.alias_generators.to_camel` on the shared `_Base` config:

- Construct models with snake_case kwargs: `Turn(number=1, line_range=(1, 5), ...)`
- Read attributes with snake_case: `turn.line_range`, `index.total_mentions`
- Serialise to camelCase JSON: `model.model_dump(by_alias=True, mode="json")`
- Parse from camelCase JSON (as written to disk): `Model.model_validate(loaded_dict)`
  (`populate_by_name=True` also accepts snake_case for internal construction)

## MCP boundary

This package is pure/MCP-free. It has no dependency on the `mcp` SDK and does not register
any tools. The MCP tool wrappers that expose `extract_story_data` and `query_story_data`
to Claude are added in the PR2 layer (`src/iw_architect/tools/story.py`).

## Tests

Story-pipeline tests live in `tests/story/`, mirroring this package's layout:

```
tests/story/
├── test_combine.py
├── test_sections.py
├── test_tracked.py
├── test_characters.py
├── test_extract.py
├── test_query.py
└── test_header.py
```

Fixtures (sample export `.txt` files) are in `tests/fixtures/`.
