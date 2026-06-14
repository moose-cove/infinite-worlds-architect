"""MCP tool wrappers for the story-extraction pipeline (PR2).

Thin adapters over the pure ``iw_architect.story`` package. Each wrapper:

1. Enforces the absolute-path contract shared by every path-taking tool
   (:func:`iw_architect.paths.require_absolute`) — the MCP server runs in a
   separate process whose working directory is not the agent's session, so a
   relative path cannot be resolved to the file the author means.
2. Invokes the pure extract/query function.
3. Serialises the resulting pydantic model to **camelCase** JSON
   (``model_dump(by_alias=True, mode="json")``) — the on-the-wire format.

These tools write nothing to world JSON. The failure convention matches the
other tool modules (``inspection.py`` / ``analysis.py``): a bare
``{"error": "..."}`` JSON object — there is **no** ``success`` envelope.
"""

from __future__ import annotations

import json

from iw_architect.paths import RelativePathError, require_absolute
from iw_architect.story.extract import extract_story_data as _extract
from iw_architect.story.query import query_story_data as _query
from iw_architect.tools.inspection import _load_world


def extract_story_data(
    input_paths: list[str],
    extraction_dir: str,
    character_list: list[dict] | None = None,
) -> str:
    """Parse story-export files into structured JSON; return a camelCase summary.

    Wraps ``iw_architect.story.extract.extract_story_data``. Enforces the
    absolute-path contract on every entry of ``input_paths`` and on
    ``extraction_dir``, then runs the pure extractor — which writes up to 5 JSON
    files atomically into ``extraction_dir`` (``manifest.json``, ``metadata.json``,
    ``turn_index.json`` always; ``tracked_state.json`` if any tracked items were
    found; ``character_index.json`` if ``character_list`` was supplied).

    input_paths: one or more absolute paths to story-export ``.txt`` files.
    extraction_dir: absolute directory to write the output files into (created if
        absent).
    character_list: optional ``[{"name": str, "aliases": [str]}]`` for the
        character index (omit to skip ``character_index.json``).

    Returns the extraction summary serialised to camelCase JSON
    (``{totalTurns, turnRange, inputFilesProcessed, hasTrackedItems,
    hasHiddenTrackedItems, filesWritten, warnings}``). On failure returns a bare
    ``{"error": "..."}``: a relative path, a missing input file, an empty
    ``input_paths``, or no Turn 1 in the inputs.
    """
    if not input_paths:
        return json.dumps(
            {"error": "input_paths must contain at least one story-export file path."}
        )

    try:
        abs_inputs = [str(require_absolute(p)) for p in input_paths]
        abs_dir = str(require_absolute(extraction_dir))
    except RelativePathError as exc:
        return json.dumps({"error": str(exc)})

    try:
        summary = _extract(abs_inputs, abs_dir, character_list=character_list)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(summary.model_dump(by_alias=True, mode="json"), indent=2)


def query_story_data(
    extraction_dir: str,
    category: str,
    turns: list[str] | None = None,
) -> str:
    """Query an extraction directory; return the category's model as camelCase JSON.

    Wraps ``iw_architect.story.query.query_story_data``. Enforces the absolute-path
    contract on ``extraction_dir``.

    extraction_dir: absolute path to a directory produced by ``extract_story_data``.
    category: one of ``manifest``, ``metadata``, ``turn_index``, ``tracked_state``,
        ``turn_detail``, ``character_index``.
    turns: optional list of turn identifiers — int-strings (``"3"``) or the literal
        ``"last"`` (resolved via the manifest's ``totalTurns``). Filters
        ``turn_index`` / ``tracked_state`` and selects the turn(s) for
        ``turn_detail`` (which re-reads the raw source lines).

    Returns the queried model serialised to camelCase JSON. On failure returns a
    bare ``{"error": "..."}``: a relative path, an unknown category, ``turn_detail``
    without ``turns``, or a missing extraction file.
    """
    try:
        abs_dir = str(require_absolute(extraction_dir))
    except RelativePathError as exc:
        return json.dumps({"error": str(exc)})

    try:
        result = _query(abs_dir, category, turns=turns)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(result.model_dump(by_alias=True, mode="json"), indent=2)


def get_character_list(world_path: str) -> str:
    """Derive a starting character list from an original world JSON.

    Pulls player characters (``possibleCharacters`` — the protagonist lives here,
    so it is never omitted) and ``NPCs``, returning each as
    ``{"name": str, "aliases": [...]}``. NPC aliases are seeded from the world's
    ``names`` field (the schema's "alternative names the NPC may go by"), so short
    forms or surnames used in the story prose still match during character indexing;
    player characters have no equivalent schema field, so their alias list starts
    empty. The author can augment any alias list in the sequel-world command step.
    Entries without a usable name are skipped (the character index matches names
    against the story text, so a nameless entry could not be indexed); names are
    de-duplicated, preserving first appearance (player characters before NPCs).

    world_path: absolute path to the original world JSON.

    Returns ``{"character_list": [{"name", "aliases"}], "source_count": int}`` where
    ``source_count`` is the number of named entries returned. On failure returns a
    bare ``{"error": "..."}`` (relative path, missing file, or invalid JSON). Writes
    nothing.
    """
    try:
        world = _load_world(world_path)
    except FileNotFoundError as exc:  # includes RelativePathError (a subclass)
        return json.dumps({"error": str(exc)})
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON in world file: {exc}"})

    character_list: list[dict] = []
    seen: set[str] = set()

    def _collect(entries: object, *, npc: bool) -> None:
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            if name in seen:
                continue
            seen.add(name)
            aliases: list[str] = []
            if npc:
                # IW NPCs carry a `names` field ("alternative names the NPC may go
                # by"); seed it as aliases so the character index matches short forms
                # / surnames in the prose. possibleCharacters have no such field.
                for alt in entry.get("names", []) or []:
                    if not isinstance(alt, str) or not alt.strip():
                        continue
                    if alt != name and alt not in aliases:
                        aliases.append(alt)
            character_list.append({"name": name, "aliases": aliases})

    _collect(world.get("possibleCharacters", []), npc=False)
    _collect(world.get("NPCs", []), npc=True)

    return json.dumps(
        {"character_list": character_list, "source_count": len(character_list)},
        indent=2,
    )
