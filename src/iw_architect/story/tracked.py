"""tracked.py — parse tracked-item blocks and generate snapshots.

``parse_tracked_items(section_text, known_names=None)``
    Parses a ``Tracked Items`` or ``Hidden Tracked Items`` section body into
    ``{key: value}`` dicts.  The hard part is finding where one item ends and
    the next begins: a YAML-typed item's value can itself contain lines that end
    in ``:`` (map keys, ``- |-`` block content), so "any line ending in a colon"
    is not an item boundary.  A line counts as an item's name line when:

    - **known names supplied** (``known_names``, usually the source world's
      ``trackedItems[*].name``): the line, minus its trailing ``:`` and any spaces
      or tabs after it, equals a known name *exactly* (raw match — a name's own
      trailing space is significant, ``Exp :`` is the name ``"Exp "``).  If the
      same name appears on several lines, the first one that opens the section or
      follows a blank line wins, else the first one.  If no line matches any known
      name, the section falls back to the rule below.
    - **no names** (fallback): the line starts with a non-whitespace character,
      ends with ``:`` (trailing spaces/tabs allowed), and is the section's first
      line or follows a blank line.  IW separates items with one blank line (an
      empty item is its name line followed by two blank lines), and YAML values
      observed so far never contain blank lines.  Known weakness: a value that
      does contain a blank line followed by a column-0 ``Something:`` line (e.g.
      a YAML block scalar with blank lines) is split there.

    Value = all lines between this name line and the next, leading blank lines
    stripped, trailing whitespace trimmed; values are kept as raw strings and are
    never YAML-parsed (AI-written YAML is often invalid).  Empty-string values are
    kept — they represent meaningful empty state.  An entirely empty section (no
    name lines) → ``None`` (not ``{}``).

``split_tracked_items(section_text, known_names=None)``
    Same parse, plus the diagnostics ``extract_story_data`` turns into manifest
    warnings: name-shaped lines that were *not* used as boundaries because they are
    not among ``known_names``.

``generate_snapshots(parsed_turns)``
    Snapshot-on-change over ``(tracked_items, hidden_tracked_items)`` per turn.
    Seeded from Turn 1 (NOT from the header's Starting Tracked Items).
    Emits a final snapshot through the max turn.
    Returns a list of :class:`~iw_architect.story.models.Snapshot` objects.
"""

from __future__ import annotations

import re
from collections.abc import Collection

from iw_architect.story.models import Snapshot, Turn

#: A line ending in ``:`` (optionally followed by spaces/tabs); ``key`` is the rest,
#: raw — leading whitespace and the name's own trailing spaces kept.
_COLON_LINE_RE = re.compile(r"^(?P<key>.*?):[ \t]*$")


def _line_key(line: str) -> str | None:
    """Return the raw key of a ``Name:`` line, or ``None`` if it is not one."""
    m = _COLON_LINE_RE.match(line)
    return m.group("key") if m else None


def _at_boundary(lines: list[str], i: int) -> bool:
    """True when line *i* opens the section or follows a blank line."""
    return i == 0 or not lines[i - 1].strip()


def _fallback_boundaries(lines: list[str]) -> list[int]:
    """Name-line indices under the no-names rule (see module docstring)."""
    out: list[int] = []
    for i, line in enumerate(lines):
        key = _line_key(line)
        if key and not key[0].isspace() and _at_boundary(lines, i):
            out.append(i)
    return out


def _known_name_boundaries(lines: list[str], names: Collection[str]) -> list[int]:
    """Name-line indices whose key exactly matches a known name (first boundary wins)."""
    by_name: dict[str, list[int]] = {}
    for i, line in enumerate(lines):
        key = _line_key(line)
        if key is not None and key in names:
            by_name.setdefault(key, []).append(i)
    chosen: list[int] = []
    for idxs in by_name.values():
        at_b = [i for i in idxs if _at_boundary(lines, i)]
        chosen.append(at_b[0] if at_b else idxs[0])
    return sorted(chosen)


def split_tracked_items(
    section_text: str | None,
    known_names: Collection[str] | None = None,
) -> tuple[dict[str, str] | None, list[str]]:
    """Parse a tracked-items section and report suspected unknown item names.

    Returns ``(items, unknown_names)``.  ``items`` is what
    :func:`parse_tracked_items` returns.  ``unknown_names`` is empty unless
    ``known_names`` was given; then it lists the keys of lines that look like
    item name lines under the fallback rule but are not known names — either
    kept inside the preceding item's value (a world item the caller did not
    list) or, when no known name matched at all, used as boundaries anyway.
    """
    if section_text is None:
        return None, []

    lines = section_text.split("\n")
    names = set(known_names) if known_names else None

    unknown: list[str] = []
    boundaries: list[int] = []
    if names is not None:
        boundaries = _known_name_boundaries(lines, names)
        unknown = [
            k
            for i in _fallback_boundaries(lines)
            if (k := _line_key(lines[i])) is not None and k not in names
        ]
    if not boundaries:
        boundaries = _fallback_boundaries(lines)
    if not boundaries:
        return None, unknown

    result: dict[str, str] = {}
    for n, start in enumerate(boundaries):
        end = boundaries[n + 1] if n + 1 < len(boundaries) else len(lines)
        key = _line_key(lines[start]) or ""  # every boundary is a colon line
        raw_value = "\n".join(lines[start + 1 : end])
        # Strip leading blank lines, then strip trailing whitespace.
        result[key] = raw_value.lstrip("\n").rstrip()

    return result, unknown


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
        When given, only lines naming one of them start a new item.

    Returns
    -------
    ``dict`` mapping item names to their raw string values, or ``None`` if the
    section is absent or contains no name lines.
    """
    return split_tracked_items(section_text, known_names)[0]


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
