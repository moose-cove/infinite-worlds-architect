"""tracked.py — parse tracked-item blocks and generate snapshots.

``parse_tracked_items(section_text, known_names=None)``
    Parses a ``Tracked Items`` or ``Hidden Tracked Items`` section body into
    ``{key: value}`` dicts.  The hard part is finding where one item ends and
    the next begins: a YAML-typed item's value can itself contain lines that end
    in ``:`` (map keys, ``- |-`` block content), so "any line ending in a colon"
    is not an item boundary.  Every rule below requires an item's name line to
    be the section's first line or to follow a blank line — IW separates items
    with one blank line (an empty item is its name line followed by two blank
    lines), and YAML values observed so far never contain blank lines.

    - **known names supplied** (``known_names``, usually the source world's
      ``trackedItems[*].name``): a boundary line's key — the line minus its
      trailing ``:`` and any spaces/tabs after it — must equal a known name
      *exactly* (raw match: a name's own trailing space is significant, ``Exp :``
      is the name ``"Exp "``).  The first such line per name wins; a repeat, or
      a known name that is not at a boundary, stays inside the value it sits in.
      Lines above the first known name are never dropped: the no-names rule is
      applied to that prefix, so they become their own (unlisted) items.  If no
      known name opens an item at all, the whole section uses the no-names rule.
    - **no names** (fallback): the boundary line must also start with a
      non-whitespace character.  A key that repeats within the section stays
      inside the preceding value rather than overwriting the first one.

    Known weaknesses: a value containing a blank line followed by a column-0
    ``Something:`` line is split there when no names are supplied; and items not
    separated by blank lines are merged (their name lines stay inside the
    previous value) in either mode.  Both are reported as diagnostics.

    Value = all lines between this name line and the next, leading blank lines
    stripped, trailing whitespace trimmed; values are kept as raw strings and are
    never YAML-parsed (AI-written YAML is often invalid).  Empty-string values are
    kept — they represent meaningful empty state.  An entirely empty section (no
    name lines) → ``None`` (not ``{}``).

``split_tracked_items(section_text, known_names=None)``
    Same parse, returned as a :class:`~iw_architect.story.models.TrackedSplit`
    with the diagnostics ``extract_story_data`` turns into manifest warnings.

``generate_snapshots(parsed_turns)``
    Snapshot-on-change over ``(tracked_items, hidden_tracked_items)`` per turn.
    Seeded from Turn 1 (NOT from the header's Starting Tracked Items).
    Emits a final snapshot through the max turn.
    Returns a list of :class:`~iw_architect.story.models.Snapshot` objects.
"""

from __future__ import annotations

import re
from collections.abc import Collection

from iw_architect.story.models import Snapshot, TrackedSplit, Turn

#: A line ending in ``:`` (optionally followed by spaces/tabs); ``key`` is the rest,
#: raw — leading whitespace and the name's own trailing spaces kept.
_COLON_LINE_RE = re.compile(r"^(?P<key>.*?):[ \t]*$")


def _line_key(line: str) -> str | None:
    """Return the raw key of a ``Name:`` line, or ``None`` if it is not one."""
    m = _COLON_LINE_RE.match(line)
    return m.group("key") if m else None


def _column0_key(line: str) -> str | None:
    """The key of a ``Name:`` line that starts at column 0, else ``None``."""
    key = _line_key(line)
    return key if key and not key[0].isspace() else None


def _at_boundary(lines: list[str], i: int) -> bool:
    """True when line *i* opens the section or follows a blank line."""
    return i == 0 or not lines[i - 1].strip()


def _fallback_boundaries(lines: list[str], start: int = 0, stop: int | None = None) -> list[int]:
    """No-names rule over ``lines[start:stop]``: column-0 key, at a boundary, key not repeated."""
    out: list[int] = []
    seen: set[str] = set()
    for i in range(start, len(lines) if stop is None else stop):
        key = _column0_key(lines[i])
        if key is not None and key not in seen and _at_boundary(lines, i):
            seen.add(key)
            out.append(i)
    return out


def split_tracked_items(
    section_text: str | None,
    known_names: Collection[str] | None = None,
) -> TrackedSplit:
    """Parse a tracked-items section into items plus mis-split diagnostics.

    See the module docstring for the boundary rules and
    :class:`~iw_architect.story.models.TrackedSplit` for the diagnostics.
    """
    if section_text is None:
        return TrackedSplit(items=None)

    lines = section_text.split("\n")
    names = set(known_names) if known_names else None
    diag: dict[str, list[str]] = {
        "merged_unlisted": [],
        "leading_unlisted": [],
        "fallback_unlisted": [],
        "listed_inside_value": [],
    }

    if names is None:
        boundaries = _fallback_boundaries(lines)
    else:
        chosen: dict[str, int] = {}
        for i, line in enumerate(lines):
            key = _line_key(line)
            if key is not None and key in names and key not in chosen and _at_boundary(lines, i):
                chosen[key] = i
        listed = set(chosen.values())
        diag["listed_inside_value"] = [
            k for i, line in enumerate(lines) if (k := _line_key(line)) in names and i not in listed
        ]
        if chosen:
            first = min(listed)
            leading = _fallback_boundaries(lines, 0, first)
            diag["leading_unlisted"] = [_line_key(lines[i]) or "" for i in leading]
            diag["merged_unlisted"] = [
                k
                for i in _fallback_boundaries(lines, first)
                if (k := _line_key(lines[i]) or "") not in names
            ]
            boundaries = sorted([*leading, *listed])
        else:
            boundaries = _fallback_boundaries(lines)
            diag["fallback_unlisted"] = [_line_key(lines[i]) or "" for i in boundaries]

    first_boundary = boundaries[0] if boundaries else len(lines)
    unassigned = sum(1 for line in lines[:first_boundary] if line.strip())
    if not boundaries:
        return TrackedSplit(items=None, unassigned_lines=unassigned, **diag)

    bset = set(boundaries)
    column0_inside = sum(
        1
        for i in range(first_boundary, len(lines))
        if i not in bset and _column0_key(lines[i]) is not None
    )

    result: dict[str, str] = {}
    for n, start in enumerate(boundaries):
        end = boundaries[n + 1] if n + 1 < len(boundaries) else len(lines)
        key = _line_key(lines[start]) or ""  # every boundary is a colon line
        raw_value = "\n".join(lines[start + 1 : end])
        # Strip leading blank lines, then strip trailing whitespace.
        result[key] = raw_value.lstrip("\n").rstrip()

    return TrackedSplit(
        items=result,
        column0_key_lines_in_values=column0_inside,
        unassigned_lines=unassigned,
        **diag,
    )


def parse_tracked_items(
    section_text: str | None,
    known_names: Collection[str] | None = None,
) -> dict | None:
    """Parse a tracked-items section body into ``{key: value}`` or ``None``.

    Parameters
    ----------
    section_text:
        The raw text of the section (after the ``----`` line), or ``None``.
    known_names:
        Optional exact tracked-item names (raw, trailing spaces significant).
        When given, only lines naming one of them start a listed item.

    Returns
    -------
    ``dict`` mapping item names to their raw string values, or ``None`` if the
    section is absent or contains no name lines.
    """
    return split_tracked_items(section_text, known_names).items


def generate_snapshots(parsed_turns: list[Turn]) -> list[Snapshot]:
    """Build snapshot-on-change list over the tracked-state pair per turn.

    Parameters
    ----------
    parsed_turns:
        List of :class:`~iw_architect.story.models.Turn` models. Sorted
        ascending by ``number`` defensively.

    Returns
    -------
    List of :class:`~iw_architect.story.models.Snapshot` objects (snake_case
    attributes; serialise with ``model_dump(by_alias=True)`` for camelCase JSON).

    An empty ``parsed_turns`` list returns ``[]``.

    The header's ``Starting Tracked Items`` is NOT an input here.
    """
    if not parsed_turns:
        return []

    turns = sorted(parsed_turns, key=lambda t: t.number)

    snapshots: list[Snapshot] = []
    first = turns[0]
    prev_state = (first.tracked_items, first.hidden_tracked_items)
    run_start = first.number
    prev_number = first.number

    for turn in turns[1:]:
        cur_state = (turn.tracked_items, turn.hidden_tracked_items)
        if cur_state != prev_state:
            snapshots.append(
                Snapshot(
                    from_turn=run_start,
                    to_turn=prev_number,
                    tracked_items=prev_state[0],
                    hidden_tracked_items=prev_state[1],
                )
            )
            run_start = turn.number
            prev_state = cur_state
        prev_number = turn.number

    # Always emit a final snapshot through the max turn.
    snapshots.append(
        Snapshot(
            from_turn=run_start,
            to_turn=turns[-1].number,
            tracked_items=prev_state[0],
            hidden_tracked_items=prev_state[1],
        )
    )

    return snapshots
