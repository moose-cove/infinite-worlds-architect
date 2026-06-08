"""query.py — query structured extraction output.

Supports 6 categories:
- ``manifest``        — return Manifest model
- ``metadata``        — return Metadata model
- ``turn_index``      — return TurnIndex model (optionally filtered by turns)
- ``tracked_state``   — return TrackedState model (optionally filtered by turns)
- ``turn_detail``     — NOT a stored file; re-reads source lines from
                        ``turn_index.json`` lineRange (raw, unparsed); returns
                        ``{"turn_detail": [TurnDetail, ...]}``
- ``character_index`` — return CharacterIndex model

The ``turns`` parameter accepts a list of strings; each element may be an
int-string (``"3"``) or ``"last"`` (resolved via ``manifest.total_turns``).

``tracked_state`` turn filtering returns snapshots that overlap the requested
turn range (``fromTurn <= turn <= toTurn``).

JSON files on disk use camelCase keys; models expose snake_case attributes.
Parse with ``Model.model_validate(loaded_dict)`` (alias_generator handles the
camelCase→snake mapping automatically).

Raises ``FileNotFoundError`` with a descriptive message if a required file is
missing.
"""

from __future__ import annotations

import json
import os

from iw_architect.story.models import (
    CharacterIndex,
    Manifest,
    Metadata,
    TrackedState,
    TurnDetail,
    TurnIndex,
)


def _read_json(path: str) -> object:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_turns(turns: list[str], total_turns: int) -> list[int]:
    resolved: list[int] = []
    for t in turns:
        if t == "last":
            resolved.append(total_turns)
        else:
            resolved.append(int(t))
    return resolved


def query_story_data(
    extraction_dir: str,
    category: str,
    turns: list[str] | None = None,
) -> Manifest | Metadata | TurnIndex | TrackedState | CharacterIndex | dict:
    """Query structured extraction output.

    Parameters
    ----------
    extraction_dir:
        Directory containing the extraction JSON files.
    category:
        One of ``manifest``, ``metadata``, ``turn_index``, ``tracked_state``,
        ``turn_detail``, ``character_index``.
    turns:
        Optional list of turn identifiers (int-strings or ``"last"``).
        Used for filtering ``turn_index``, ``tracked_state``, and for
        selecting the turn in ``turn_detail``.

    Returns
    -------
    A pydantic model for the queried category, or ``{"turn_detail": [...]}``
    for ``turn_detail``.  All models expose snake_case attributes; serialise
    with ``model_dump(by_alias=True)`` for camelCase JSON.

    Raises
    ------
    ValueError
        If ``category`` is not one of the 6 valid values, or if ``turn_detail``
        is requested without a ``turns`` argument.
    FileNotFoundError
        If a required JSON file is missing from ``extraction_dir``.
    """
    valid_categories = {
        "manifest",
        "metadata",
        "turn_index",
        "tracked_state",
        "turn_detail",
        "character_index",
    }
    if category not in valid_categories:
        valid = sorted(valid_categories)
        raise ValueError(f"Unknown category {category!r}; expected one of {valid}")

    manifest_path = os.path.join(extraction_dir, "manifest.json")
    manifest_data = _read_json(manifest_path)
    manifest_model = Manifest.model_validate(manifest_data)
    total_turns: int = manifest_model.total_turns

    resolved: list[int] = _resolve_turns(turns, total_turns) if turns else []

    if category == "manifest":
        return manifest_model

    if category == "metadata":
        return Metadata.model_validate(_read_json(os.path.join(extraction_dir, "metadata.json")))

    if category == "turn_index":
        data = _read_json(os.path.join(extraction_dir, "turn_index.json"))
        model = TurnIndex.model_validate(data)
        if resolved:
            filtered = [t for t in model.turns if t.number in resolved]
            # Return a new TurnIndex with filtered turns (frozen model — reconstruct).
            return TurnIndex(turns=filtered)
        return model

    if category == "tracked_state":
        data = _read_json(os.path.join(extraction_dir, "tracked_state.json"))
        model = TrackedState.model_validate(data)
        if resolved:
            filtered = [
                s for s in model.snapshots if any(s.from_turn <= r <= s.to_turn for r in resolved)
            ]
            return TrackedState(snapshots=filtered)
        return model

    if category == "character_index":
        return CharacterIndex.model_validate(
            _read_json(os.path.join(extraction_dir, "character_index.json"))
        )

    # category == "turn_detail"
    if not turns:
        raise ValueError("turn_detail requires at least one turn in the 'turns' argument")

    turn_index_data = _read_json(os.path.join(extraction_dir, "turn_index.json"))
    turn_index_model = TurnIndex.model_validate(turn_index_data)

    details: list[TurnDetail] = []
    for turn_num in resolved:
        # Find the turn entry (snake_case attribute access).
        entry = next((t for t in turn_index_model.turns if t.number == turn_num), None)
        if entry is None:
            raise ValueError(f"Turn {turn_num} not found in turn_index.json")
        source = entry.source
        start, end = entry.line_range[0], entry.line_range[1]

        if not os.path.exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        with open(source, encoding="utf-8") as fh:
            all_lines = fh.read().replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # line_range is 1-indexed inclusive.
        raw_lines = all_lines[start - 1 : end]
        details.append(
            TurnDetail(
                turn=turn_num,
                source=source,
                raw="\n".join(raw_lines),
            )
        )

    return {"turn_detail": details}
