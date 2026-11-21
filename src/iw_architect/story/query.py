"""query.py — query structured extraction output.

Supports 6 categories:
- ``manifest``        — return Manifest model
- ``metadata``        — return Metadata model
- ``turn_index``      — return TurnIndex model (optionally filtered by turns)
- ``tracked_state``   — return TrackedState model (optionally filtered by turns)
- ``turn_detail``     — NOT a stored file; re-reads source lines from
                        ``turn_index.json`` lineRange (raw, unparsed); returns
                        a ``TurnDetailResult`` model
- ``character_index`` — return CharacterIndex model

The ``turns`` parameter accepts a list; each element may be an
int (``3``), an int-string (``"3"``) or ``"last"`` (resolved via ``manifest.total_turns``).

``tracked_state`` turn filtering returns snapshots that overlap the requested
turn range (``fromTurn <= turn <= toTurn``).

``items`` (``tracked_state`` / ``turn_index`` only) projects every
``trackedItems`` / ``hiddenTrackedItems`` dict onto the named items.  A name
matches exactly first, then case-insensitively with surrounding whitespace
stripped (``"Exp"`` finds ``"Exp "``); an unknown name raises ``ValueError``
listing the available names.  ``changes_only`` (``tracked_state`` with
``items`` only) then merges adjacent snapshots whose projected values are equal,
so the result has one entry per run of unchanged values.  Order of operations:
filter by ``turns``, project onto ``items``, merge.

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
    Snapshot,
    TrackedState,
    TurnDetail,
    TurnDetailResult,
    TurnIndex,
)


def _read_json(path: str) -> object:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_turns(turns: list[str | int], total_turns: int) -> list[int]:
    resolved: list[int] = []
    for t in turns:
        if t == "last":
            resolved.append(total_turns)
        else:
            resolved.append(int(t))
    return resolved


def _available_items(states: list[tuple[dict | None, dict | None]]) -> list[str]:
    """Every tracked / hidden item name across *states*, first-appearance order."""
    seen: dict[str, None] = {}
    for tracked, hidden in states:
        for d in (tracked, hidden):
            for key in d or {}:
                seen.setdefault(key, None)
    return list(seen)


def _resolve_items(requested: list[str], available: list[str]) -> list[str]:
    """Map requested names to stored keys: exact first, then case/whitespace-insensitive."""
    resolved: list[str] = []
    unknown: list[str] = []
    for name in requested:
        if name in available:
            match = name
        else:
            folded = name.strip().casefold()
            candidates = [a for a in available if a.strip().casefold() == folded]
            if len(candidates) > 1:
                raise ValueError(f"Item name {name!r} is ambiguous; it matches {candidates}")
            if not candidates:
                unknown.append(name)
                continue
            match = candidates[0]
        if match not in resolved:
            resolved.append(match)
    if unknown:
        raise ValueError(f"Unknown tracked item name(s) {unknown}; available items: {available}")
    return resolved


def _project(d: dict[str, str] | None, keys: list[str]) -> dict[str, str] | None:
    """Keep only *keys* (in *keys* order); an absent section stays ``None``."""
    if d is None:
        return None
    return {k: d[k] for k in keys if k in d}


def query_story_data(
    extraction_dir: str,
    category: str,
    turns: list[str | int] | None = None,
    items: list[str] | None = None,
    changes_only: bool = False,
) -> Manifest | Metadata | TurnIndex | TrackedState | CharacterIndex | TurnDetailResult:
    """Query structured extraction output.

    Parameters
    ----------
    extraction_dir:
        Directory containing the extraction JSON files.
    category:
        One of ``manifest``, ``metadata``, ``turn_index``, ``tracked_state``,
        ``turn_detail``, ``character_index``.
    turns:
        Optional list of turn identifiers (ints, int-strings or ``"last"``).
        Used for filtering ``turn_index``, ``tracked_state``, and for
        selecting the turn in ``turn_detail``.
    items:
        Optional tracked-item names (``tracked_state`` / ``turn_index`` only):
        project both tracked dicts onto these items.
    changes_only:
        ``tracked_state`` with ``items`` only: merge adjacent snapshots whose
        projected values are equal (first ``fromTurn``, last ``toTurn``).

    Returns
    -------
    A pydantic model for the queried category (``turn_detail`` returns a
    :class:`~iw_architect.story.models.TurnDetailResult`).  All models expose
    snake_case attributes; serialise with ``model_dump(by_alias=True)`` for
    camelCase JSON.

    Raises
    ------
    ValueError
        If ``category`` is not one of the 6 valid values, if ``turn_detail``
        is requested without a ``turns`` argument, if ``items`` / ``changes_only``
        is used with a category that does not support it (or ``changes_only``
        without ``items``), or if an item name is unknown or ambiguous.
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
    if items is not None and category not in {"tracked_state", "turn_index"}:
        raise ValueError("items is only supported for the tracked_state and turn_index categories")
    if changes_only and category != "tracked_state":
        raise ValueError("changes_only is only supported for the tracked_state category")
    if changes_only and not items:
        raise ValueError("changes_only requires items (the tracked items to compare)")

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
        selected = model.turns
        if resolved:
            selected = [t for t in model.turns if t.number in resolved]
        if items:
            keys = _resolve_items(
                items,
                _available_items([(t.tracked_items, t.hidden_tracked_items) for t in model.turns]),
            )
            selected = [
                t.model_copy(
                    update={
                        "tracked_items": _project(t.tracked_items, keys),
                        "hidden_tracked_items": _project(t.hidden_tracked_items, keys),
                    }
                )
                for t in selected
            ]
        if resolved or items:
            # Return a new TurnIndex (frozen model — reconstruct).
            return TurnIndex(turns=selected)
        return model

    if category == "tracked_state":
        data = _read_json(os.path.join(extraction_dir, "tracked_state.json"))
        model = TrackedState.model_validate(data)
        # Keep each snapshot's position so changes_only merges only true neighbours.
        indexed = list(enumerate(model.snapshots))
        if resolved:
            indexed = [
                (i, s) for i, s in indexed if any(s.from_turn <= r <= s.to_turn for r in resolved)
            ]
        if not items:
            return TrackedState(snapshots=[s for _, s in indexed]) if resolved else model
        keys = _resolve_items(
            items,
            _available_items([(s.tracked_items, s.hidden_tracked_items) for s in model.snapshots]),
        )
        projected = [
            (
                i,
                Snapshot(
                    from_turn=s.from_turn,
                    to_turn=s.to_turn,
                    tracked_items=_project(s.tracked_items, keys),
                    hidden_tracked_items=_project(s.hidden_tracked_items, keys),
                ),
            )
            for i, s in indexed
        ]
        if not changes_only:
            return TrackedState(snapshots=[s for _, s in projected])
        merged: list[tuple[int, Snapshot]] = []
        for i, s in projected:
            if merged:
                prev_i, prev = merged[-1]
                same = (prev.tracked_items, prev.hidden_tracked_items) == (
                    s.tracked_items,
                    s.hidden_tracked_items,
                )
                if same and i == prev_i + 1:
                    merged[-1] = (i, prev.model_copy(update={"to_turn": s.to_turn}))
                    continue
            merged.append((i, s))
        return TrackedState(snapshots=[s for _, s in merged])

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

    return TurnDetailResult(turn_detail=details)
