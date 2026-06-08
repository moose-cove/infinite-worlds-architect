"""extract.py — orchestrate full story-export extraction.

Writes up to 5 files atomically into ``extraction_dir``:
- ``manifest.json``        always
- ``metadata.json``        always
- ``turn_index.json``      always
- ``tracked_state.json``   only if any tracked items found
- ``character_index.json`` only if ``character_list`` provided

Atomic write: temp file ``extraction_dir/.tmp-<name>.json`` → ``os.replace``
(same filesystem, so the replace is atomic on POSIX and on Windows Vista+).

Returns an :class:`~iw_architect.story.models.ExtractionSummary` model with
snake_case attributes. Casing maps across the serialization boundary: the Python
attribute ``summary.total_turns`` ↔ the JSON key ``totalTurns``. ``manifest.json``
on disk is pure camelCase (via ``Manifest.model_dump(by_alias=True)``); when
``query_story_data`` reads it back, the ``totalTurns`` key populates the model's
``total_turns`` attribute.

Re-run is idempotent — previous output files are overwritten.
"""

from __future__ import annotations

import json
import os

from iw_architect.story.characters import index_characters
from iw_architect.story.combine import combine
from iw_architect.story.header import parse_header
from iw_architect.story.models import (
    ExtractionSummary,
    Manifest,
    Source,
    TrackedState,
    Turn,
    TurnIndex,
    TurnRange,
)
from iw_architect.story.sections import parse_turn_sections
from iw_architect.story.tracked import generate_snapshots, parse_tracked_items


def _atomic_write(extraction_dir: str, name: str, data: object) -> None:
    """Write *data* as JSON to ``extraction_dir/<name>.json`` atomically."""
    final_path = os.path.join(extraction_dir, f"{name}.json")
    tmp_path = os.path.join(extraction_dir, f".tmp-{name}.json")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, final_path)


def extract_story_data(
    input_paths: list[str],
    extraction_dir: str,
    character_list: list[dict] | None = None,
) -> ExtractionSummary:
    """Extract a story export set and write structured JSON output files.

    Parameters
    ----------
    input_paths:
        One or more paths to story-export ``.txt`` files.
    extraction_dir:
        Directory in which to write output files (created automatically if
        absent).
    character_list:
        Optional list of ``{"name": str, "aliases": [str]}`` dicts for
        character indexing.

    Returns
    -------
    :class:`~iw_architect.story.models.ExtractionSummary` with snake_case
    attributes.  Access fields as ``summary.total_turns``,
    ``summary.turn_range.min``, etc.  Serialise with
    ``model_dump(by_alias=True)`` for the camelCase API shape.

    Notes
    -----
    Each ``turn_index`` entry's ``lineRange`` is 1-indexed inclusive and
    **marker-inclusive**: it starts at the ``-- Turn N --`` marker line itself.

    Raises
    ------
    ValueError
        If no Turn 1 is present (propagated from ``combine``).
    """
    os.makedirs(extraction_dir, exist_ok=True)

    combined = combine(input_paths)
    header_text = combined["header"]
    raw_turns = combined["turns"]
    warnings: list[str] = list(combined["warnings"])

    # Build per-source line arrays for line_range computation and char indexing.
    source_lines: dict[str, list[str]] = {}
    source_text: dict[str, str] = {}
    for t in raw_turns:
        src = t["source"]
        if src not in source_lines:
            with open(src, encoding="utf-8") as fh:
                raw = fh.read().replace("\r\n", "\n").replace("\r", "\n")
            source_lines[src] = raw.split("\n")
            source_text[src] = raw

    # Parse metadata from header — returns a Metadata model.
    metadata = parse_header(header_text)

    # Parse each turn — compute line_range relative to its source file.
    parsed_turns: list[dict] = []
    for t in raw_turns:
        number = t["number"]
        content = t["content"]
        src = t["source"]

        sections = parse_turn_sections(content, number)
        tracked = parse_tracked_items(sections["tracked_items"])
        hidden = parse_tracked_items(sections["hidden_tracked_items"])

        # Compute line_range: find the turn marker in the source file.
        src_lines = source_lines[src]
        marker = f"-- Turn {number} --"
        start_line = None
        for idx, line in enumerate(src_lines):
            if line.rstrip("\r") == marker:
                start_line = idx + 1  # 1-indexed line of the marker itself
                break

        if start_line is None:
            # Fallback: shouldn't happen if combine worked correctly.
            line_range = (1, 1)
        else:
            # end_line: last non-empty line before next turn marker or EOF.
            next_marker_line = None
            # Scan lines after the marker to find the next turn marker.
            for idx in range(start_line, len(src_lines)):
                stripped = src_lines[idx].rstrip("\r")
                if stripped.startswith("-- Turn ") and stripped.endswith(" --"):
                    next_marker_line = idx + 1  # 1-indexed
                    break
            if next_marker_line is not None:
                end_line = next_marker_line - 1
            else:
                end_line = len(src_lines)
            # Trim trailing blank lines.
            while end_line > start_line and not src_lines[end_line - 1].strip():
                end_line -= 1
            line_range = (start_line, end_line)

        parsed_turns.append(
            {
                "number": number,
                "action": sections["action"],
                "outcome": sections["outcome"],
                "secret_info": sections["secret_info"],
                "tracked_items": tracked,
                "hidden_tracked_items": hidden,
                "source": src,
                "line_range": line_range,
            }
        )

    # Build Turn models and TurnIndex.
    turn_models = [Turn(**t) for t in parsed_turns]
    turn_index = TurnIndex(turns=turn_models)

    # Build tracked_state (only if any tracked items found).
    has_tracked = any(
        t["tracked_items"] is not None or t["hidden_tracked_items"] is not None
        for t in parsed_turns
    )
    tracked_state: TrackedState | None = None
    if has_tracked:
        snapshots = generate_snapshots(parsed_turns)
        tracked_state = TrackedState(snapshots=snapshots)

    # Build character_index (only if character_list provided).
    char_index = None
    char_warnings: list[str] = []
    if character_list:
        char_index, char_warnings = index_characters(parsed_turns, source_text, character_list)
    warnings.extend(char_warnings)

    # Build the written-files list.
    files_written: list[str] = ["manifest.json", "metadata.json", "turn_index.json"]
    if tracked_state is not None:
        files_written.append("tracked_state.json")
    if char_index is not None:
        files_written.append("character_index.json")

    # Derive summary fields (spec §3 contract).
    numbers = [t["number"] for t in parsed_turns]
    turn_range = TurnRange(min=min(numbers), max=max(numbers))
    has_tracked_items = any(t["tracked_items"] is not None for t in parsed_turns)
    has_hidden_items = any(t["hidden_tracked_items"] is not None for t in parsed_turns)

    # Provenance: group turn numbers by source file (first-appearance order).
    sources_map: dict[str, list[int]] = {}
    for t in parsed_turns:
        sources_map.setdefault(t["source"], []).append(t["number"])
    sources = [Source(path=src, turns=sorted(nums)) for src, nums in sources_map.items()]

    # Build the manifest model (pure camelCase on disk).
    manifest = Manifest(
        total_turns=len(parsed_turns),
        turn_range=turn_range,
        input_files_processed=len(input_paths),
        has_tracked_items=has_tracked_items,
        has_hidden_tracked_items=has_hidden_items,
        files_written=files_written,
        warnings=warnings,
        sources=sources,
    )

    # Write files atomically (all camelCase via model_dump).
    _atomic_write(extraction_dir, "manifest", manifest.model_dump(by_alias=True, mode="json"))
    _atomic_write(extraction_dir, "metadata", metadata.model_dump(by_alias=True, mode="json"))
    _atomic_write(extraction_dir, "turn_index", turn_index.model_dump(by_alias=True, mode="json"))
    if tracked_state is not None:
        _atomic_write(
            extraction_dir,
            "tracked_state",
            tracked_state.model_dump(by_alias=True, mode="json"),
        )
    if char_index is not None:
        _atomic_write(
            extraction_dir,
            "character_index",
            char_index.model_dump(by_alias=True, mode="json"),
        )

    # Return ExtractionSummary (no sources — that's Manifest-only).
    return ExtractionSummary(
        total_turns=len(parsed_turns),
        turn_range=turn_range,
        input_files_processed=len(input_paths),
        has_tracked_items=has_tracked_items,
        has_hidden_tracked_items=has_hidden_items,
        files_written=files_written,
        warnings=warnings,
    )
