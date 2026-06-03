"""extract.py — orchestrate full story-export extraction.

Writes up to 5 files atomically into ``extraction_dir``:
- ``manifest.json``        always
- ``metadata.json``        always
- ``turn_index.json``      always
- ``tracked_state.json``   only if any tracked items found
- ``character_index.json`` only if ``character_list`` provided

Atomic write: temp file ``extraction_dir/.tmp-<name>.json`` → ``os.replace``
(same filesystem, so the replace is atomic on POSIX and on Windows Vista+).

Returns a manifest-summary dict (the same shape written to ``manifest.json``).

Re-run is idempotent — previous output files are overwritten.
"""

from __future__ import annotations

import json
import os

from iw_architect.story.characters import index_characters
from iw_architect.story.combine import combine
from iw_architect.story.header import parse_header
from iw_architect.story.sections import parse_turn_sections
from iw_architect.story.tracked import generate_snapshots, parse_tracked_items


def _atomic_write(extraction_dir: str, name: str, data: object) -> None:
    """Write *data* as JSON to ``extraction_dir/<name>.json`` atomically."""
    final_path = os.path.join(extraction_dir, f"{name}.json")
    tmp_path = os.path.join(extraction_dir, f".tmp-{name}.json")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, final_path)


def _count_lines(text: str) -> list[str]:
    return text.split("\n")


def extract_story_data(
    input_paths: list[str],
    extraction_dir: str,
    character_list: list[dict] | None = None,
) -> dict:
    """Extract a story export set and write structured JSON output files.

    Parameters
    ----------
    input_paths:
        One or more paths to story-export ``.txt`` files.
    extraction_dir:
        Directory in which to write output files (must exist or be created
        by the caller before this function is invoked).
    character_list:
        Optional list of ``{"name": str, "aliases": [str]}`` dicts for
        character indexing.

    Returns
    -------
    Manifest-summary dict (same content as ``manifest.json``).

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

    # Build per-source line arrays for lineRange computation and char indexing.
    source_lines: dict[str, list[str]] = {}
    source_text: dict[str, str] = {}
    for t in raw_turns:
        src = t["source"]
        if src not in source_lines:
            with open(src, encoding="utf-8") as fh:
                raw = fh.read().replace("\r\n", "\n").replace("\r", "\n")
            source_lines[src] = raw.split("\n")
            source_text[src] = raw

    # Parse metadata from header.
    metadata = parse_header(header_text)
    metadata["objective"] = None

    # Parse each turn — compute lineRange relative to its source file.
    parsed_turns: list[dict] = []
    for t in raw_turns:
        number = t["number"]
        content = t["content"]
        src = t["source"]

        sections = parse_turn_sections(content, number)
        tracked = parse_tracked_items(sections["trackedItems"])
        hidden = parse_tracked_items(sections["hiddenTrackedItems"])

        # Compute lineRange: find the turn marker in the source file.
        src_lines = source_lines[src]
        marker = f"-- Turn {number} --"
        start_line = None
        for idx, line in enumerate(src_lines):
            if line.rstrip("\r") == marker:
                start_line = idx + 1  # 1-indexed line of the marker itself
                break

        if start_line is None:
            # Fallback: shouldn't happen if combine worked correctly.
            line_range = [1, 1]
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
            line_range = [start_line, end_line]

        parsed_turns.append(
            {
                "number": number,
                "action": sections["action"],
                "outcome": sections["outcome"],
                "secretInfo": sections["secretInfo"],
                "trackedItems": tracked,
                "hiddenTrackedItems": hidden,
                "source": src,
                "lineRange": line_range,
            }
        )

    # Build turn_index.
    turn_index = {"turns": parsed_turns}

    # Build tracked_state (only if any tracked items found).
    has_tracked = any(
        t["trackedItems"] is not None or t["hiddenTrackedItems"] is not None for t in parsed_turns
    )
    tracked_state = None
    if has_tracked:
        snapshots = generate_snapshots(parsed_turns)
        tracked_state = {"snapshots": snapshots}

    # Build character_index (only if character_list provided).
    char_index = None
    char_warnings: list[str] = []
    if character_list:
        char_index, char_warnings = index_characters(parsed_turns, source_text, character_list)
    warnings.extend(char_warnings)

    # Build manifest.
    files_written: list[str] = ["manifest.json", "metadata.json", "turn_index.json"]
    if tracked_state is not None:
        files_written.append("tracked_state.json")
    if char_index is not None:
        files_written.append("character_index.json")

    manifest = {
        "input_paths": [os.path.abspath(p) for p in input_paths],
        "extraction_dir": os.path.abspath(extraction_dir),
        "total_turns": len(parsed_turns),
        "files_written": files_written,
        "warnings": warnings,
    }

    # Write files atomically.
    _atomic_write(extraction_dir, "manifest", manifest)
    _atomic_write(extraction_dir, "metadata", metadata)
    _atomic_write(extraction_dir, "turn_index", turn_index)
    if tracked_state is not None:
        _atomic_write(extraction_dir, "tracked_state", tracked_state)
    if char_index is not None:
        _atomic_write(extraction_dir, "character_index", char_index)

    return manifest
