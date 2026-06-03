"""query.py — query structured extraction output.

Supports 6 categories:
- ``manifest``        — return manifest.json contents
- ``metadata``        — return metadata.json contents
- ``turn_index``      — return turn_index.json (optionally filtered by turns)
- ``tracked_state``   — return tracked_state.json (optionally filtered by turns)
- ``turn_detail``     — NOT a stored file; re-reads the source lines from
                        ``turn_index.json`` lineRange (raw, unparsed)
- ``character_index`` — return character_index.json

The ``turns`` parameter accepts a list of strings; each element may be an
int-string (``"3"``) or ``"last"`` (resolved via ``manifest.total_turns``).

``tracked_state`` turn filtering returns snapshots that overlap the requested
turn range (``fromTurn <= turn <= toTurn``).

Raises ``FileNotFoundError`` with a descriptive message if a required file is
missing.
"""

from __future__ import annotations

import json
import os


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
) -> dict:
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
    A dict representing the queried data.

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
    manifest = _read_json(manifest_path)
    total_turns: int = manifest["total_turns"]  # type: ignore[index]

    resolved: list[int] = _resolve_turns(turns, total_turns) if turns else []

    if category == "manifest":
        return manifest  # type: ignore[return-value]

    if category == "metadata":
        return _read_json(os.path.join(extraction_dir, "metadata.json"))  # type: ignore[return-value]

    if category == "turn_index":
        data = _read_json(os.path.join(extraction_dir, "turn_index.json"))
        if resolved:
            data["turns"] = [t for t in data["turns"] if t["number"] in resolved]  # type: ignore[index]
        return data  # type: ignore[return-value]

    if category == "tracked_state":
        data = _read_json(os.path.join(extraction_dir, "tracked_state.json"))
        if resolved:
            data["snapshots"] = [  # type: ignore[index]
                s
                for s in data["snapshots"]  # type: ignore[index]
                if any(s["fromTurn"] <= r <= s["toTurn"] for r in resolved)
            ]
        return data  # type: ignore[return-value]

    if category == "character_index":
        return _read_json(os.path.join(extraction_dir, "character_index.json"))  # type: ignore[return-value]

    # category == "turn_detail"
    if not turns:
        raise ValueError("turn_detail requires at least one turn in the 'turns' argument")

    turn_index_data = _read_json(os.path.join(extraction_dir, "turn_index.json"))
    turns_list = turn_index_data["turns"]  # type: ignore[index]

    results: list[dict] = []
    for turn_num in resolved:
        # Find the turn entry.
        entry = next((t for t in turns_list if t["number"] == turn_num), None)
        if entry is None:
            raise ValueError(f"Turn {turn_num} not found in turn_index.json")
        source = entry["source"]
        line_range = entry["lineRange"]
        start, end = line_range[0], line_range[1]

        if not os.path.exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        with open(source, encoding="utf-8") as fh:
            all_lines = fh.read().replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # lineRange is 1-indexed inclusive.
        raw_lines = all_lines[start - 1 : end]
        results.append(
            {
                "turn": turn_num,
                "source": source,
                "lineRange": line_range,
                "raw": "\n".join(raw_lines),
            }
        )

    return {"turn_detail": results}
