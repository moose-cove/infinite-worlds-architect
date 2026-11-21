"""extract.py — orchestrate full story-export extraction.

Writes up to 5 files atomically into ``extraction_dir``:
- ``manifest.json``        always
- ``metadata.json``        always
- ``turn_index.json``      always
- ``tracked_state.json``   only if any tracked items found
- ``character_index.json`` only if ``character_list`` provided

Tracked-item boundaries: pass ``tracked_item_names`` (the source world's
``trackedItems[*].name``) so multi-line YAML values whose lines end in ``:`` are
not split into phantom items — see :mod:`iw_architect.story.tracked`.  Suspected
mis-splits are reported in ``manifest.warnings``.

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
    TrackedSplit,
    TrackedState,
    Turn,
    TurnIndex,
    TurnRange,
)
from iw_architect.story.sections import parse_turn_sections
from iw_architect.story.tracked import generate_snapshots, split_tracked_items

#: Cap on per-turn key-set-change warnings in the no-names fallback.
_MAX_KEYSET_WARNINGS = 10
#: Cap on per-name diagnostic warnings in known-names mode.
_MAX_NAME_WARNINGS = 20
#: Cap on turn numbers / names listed inside a single warning.
_MAX_LISTED = 8

_SECTIONS = (
    ("Tracked Items", "tracked_items"),
    ("Hidden Tracked Items", "hidden_tracked_items"),
)

#: Known-names diagnostic kind → warning template (``{label}``, ``{line}``, ``{turns}``).
_NAME_WARNING_TEMPLATES = {
    "merged_unlisted": (
        "{label}: line {line} is not in tracked_item_names, so it was kept inside the value "
        "of the listed item above it (turns {turns}). Add the name if it is a real item."
    ),
    "leading_unlisted": (
        "{label}: line {line} comes before the first listed item and is not in "
        "tracked_item_names; it was kept as its own item (turns {turns}). Add the name if it "
        "is a real item."
    ),
    "fallback_unlisted": (
        "{label}: no line matched a name in tracked_item_names, so the blank-line rule was "
        "used and line {line} became an item (turns {turns}). Check that the names belong "
        "to the world that produced this story."
    ),
    "listed_inside_value": (
        "{label}: line {line} matches a name in tracked_item_names but does not open the "
        "section or follow a blank line, or repeats an earlier name line, so it was kept "
        "inside the value it sits in (turns {turns})."
    ),
}


def _fmt_list(values: list) -> str:
    """Render up to ``_MAX_LISTED`` values, noting how many were left out."""
    shown = ", ".join(repr(v) for v in values[:_MAX_LISTED])
    extra = len(values) - _MAX_LISTED
    return f"{shown}, … (+{extra} more)" if extra > 0 else shown


def _tracked_item_warnings(
    parsed_turns: list[Turn],
    tracked_item_names: list[str] | None,
    splits: list[tuple[int, str, TrackedSplit]],
) -> list[str]:
    """Manifest warnings that flag a suspected tracked-item mis-split.

    ``splits`` holds ``(turn number, section label, TrackedSplit)`` for every
    section that was present.
    """
    warnings: list[str] = []

    unassigned_turns = sorted({n for n, _, s in splits if s.unassigned_lines})
    if unassigned_turns:
        total = sum(s.unassigned_lines for _, _, s in splits)
        warnings.append(
            f"{total} non-blank line(s) before the first tracked-item name could not be "
            f"assigned to any item and were dropped (turns {_fmt_list(unassigned_turns)})."
        )

    if tracked_item_names:
        by_kind: dict[tuple[str, str, str], list[int]] = {}
        for number, label, split in splits:
            for kind in _NAME_WARNING_TEMPLATES:
                for key in getattr(split, kind):
                    turns = by_kind.setdefault((kind, label, key), [])
                    if number not in turns:
                        turns.append(number)
        name_warnings = [
            _NAME_WARNING_TEMPLATES[kind].format(
                label=label, line=repr(key + ":"), turns=_fmt_list(turns)
            )
            for (kind, label, key), turns in by_kind.items()
        ]
        warnings.extend(name_warnings[:_MAX_NAME_WARNINGS])
        if len(name_warnings) > _MAX_NAME_WARNINGS:
            warnings.append(
                f"… {len(name_warnings) - _MAX_NAME_WARNINGS} more tracked-item name "
                "warnings not listed."
            )
        seen: set[str] = set()
        for t in parsed_turns:
            for _, attr in _SECTIONS:
                seen.update(getattr(t, attr) or {})
        missing = [n for n in tracked_item_names if n not in seen]
        if missing:
            warnings.append(
                f"tracked_item_names never matched a name line in any turn: {_fmt_list(missing)}. "
                "Check the names against the export (matching is exact, trailing spaces included)."
            )
        return warnings

    # No names: items normally appear on every turn, so a key set that changes
    # from one turn to the next is a strong sign a multi-line value was split.
    ordered = sorted(parsed_turns, key=lambda t: t.number)
    changes: list[str] = []
    for label, attr in _SECTIONS:
        for prev, cur in zip(ordered, ordered[1:], strict=False):
            a, b = getattr(prev, attr), getattr(cur, attr)
            if a is None or b is None or a.keys() == b.keys():
                continue
            added = [k for k in b if k not in a]
            removed = [k for k in a if k not in b]
            changes.append(
                f"{label}: keys changed between turns {prev.number} and {cur.number} "
                f"(added: [{_fmt_list(added)}]; removed: [{_fmt_list(removed)}]) — possibly a "
                "multi-line value split into phantom items; re-run with tracked_item_names "
                "to anchor item boundaries."
            )
    warnings.extend(changes[:_MAX_KEYSET_WARNINGS])
    if len(changes) > _MAX_KEYSET_WARNINGS:
        warnings.append(
            f"… {len(changes) - _MAX_KEYSET_WARNINGS} more tracked-item key-set changes not listed."
        )

    # One aggregated note: column-0 "Key:" lines that stayed inside values.
    inside = [(n, s.column0_key_lines_in_values) for n, _, s in splits]
    total_inside = sum(c for _, c in inside)
    if total_inside:
        turns_inside = len({n for n, c in inside if c})
        warnings.append(
            f"Without tracked_item_names, {total_inside} column-0 'Key:' line(s) on "
            f"{turns_inside} turn(s) were kept inside tracked-item values, because only a name "
            "line that opens the section or follows a blank line starts a new item. That is "
            "expected for YAML map values; but if this export does not separate items with "
            "blank lines, items were merged. Pass tracked_item_names to anchor item boundaries."
        )
    return warnings


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
    tracked_item_names: list[str] | None = None,
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
    tracked_item_names:
        Optional exact tracked-item names (raw — trailing spaces are significant),
        normally every ``trackedItems[*].name`` of the world that produced the
        story, hidden items included.  Applied to both the ``Tracked Items`` and
        ``Hidden Tracked Items`` sections: only a line naming one of them starts a
        listed item, and the header's ``Starting Tracked Items`` are parsed with
        the same names.  Without it, a blank-line boundary heuristic is used.

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
    header_text = combined.header
    raw_turns = combined.turns
    warnings: list[str] = list(combined.warnings)

    # Build per-source line arrays for line_range computation and char indexing.
    source_lines: dict[str, list[str]] = {}
    source_text: dict[str, str] = {}
    for t in raw_turns:
        src = t.source
        if src not in source_lines:
            with open(src, encoding="utf-8") as fh:
                raw = fh.read().replace("\r\n", "\n").replace("\r", "\n")
            source_lines[src] = raw.split("\n")
            source_text[src] = raw

    # Parse metadata from header — returns a Metadata model.
    metadata = parse_header(header_text, tracked_item_names)

    # Parse each turn — compute line_range relative to its source file.
    parsed_turns: list[Turn] = []
    splits: list[tuple[int, str, TrackedSplit]] = []
    for t in raw_turns:
        number = t.number
        content = t.content
        src = t.source

        sections = parse_turn_sections(content, number)
        tracked_split = split_tracked_items(sections.tracked_items, tracked_item_names)
        hidden_split = split_tracked_items(sections.hidden_tracked_items, tracked_item_names)
        tracked, hidden = tracked_split.items, hidden_split.items
        for (label, _), raw_section, split in zip(
            _SECTIONS,
            (sections.tracked_items, sections.hidden_tracked_items),
            (tracked_split, hidden_split),
            strict=True,
        ):
            if raw_section is not None:
                splits.append((number, label, split))

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
            Turn(
                number=number,
                action=sections.action,
                outcome=sections.outcome,
                secret_info=sections.secret_info,
                tracked_items=tracked,
                hidden_tracked_items=hidden,
                source=src,
                line_range=line_range,
            )
        )

    warnings.extend(_tracked_item_warnings(parsed_turns, tracked_item_names, splits))

    # Build TurnIndex directly from the parsed Turn models.
    turn_index = TurnIndex(turns=parsed_turns)

    # Build tracked_state (only if any tracked items found).
    has_tracked = any(
        t.tracked_items is not None or t.hidden_tracked_items is not None for t in parsed_turns
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
    numbers = [t.number for t in parsed_turns]
    turn_range = TurnRange(min=min(numbers), max=max(numbers))
    has_tracked_items = any(t.tracked_items is not None for t in parsed_turns)
    has_hidden_items = any(t.hidden_tracked_items is not None for t in parsed_turns)

    # Provenance: group turn numbers by source file (first-appearance order).
    sources_map: dict[str, list[int]] = {}
    for t in parsed_turns:
        sources_map.setdefault(t.source, []).append(t.number)
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
