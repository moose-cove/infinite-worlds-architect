"""tracked.py — parse tracked-item blocks and generate snapshots.

``parse_tracked_items(section_text)``
    Parses a ``Tracked Items`` or ``Hidden Tracked Items`` section body into
    ``{key: value}`` dicts.  Rules (spec §2):

    - Key line regex: ``^(?P<key>[^\\n:][^\\n]*?):[ \\t]*$`` (re.MULTILINE).
    - Value = all lines between this key and the next key, leading blank lines
      stripped, trailing whitespace trimmed, but the value itself may be
      multi-line.
    - Empty-string values are kept (not dropped) — they represent meaningful
      empty state.
    - An entirely empty section (no key lines) → ``None`` (not ``{}``).

``generate_snapshots(parsed_turns)``
    Snapshot-on-change over ``(trackedItems, hiddenTrackedItems)`` per turn.
    Seeded from Turn 1 (NOT from the header's Starting Tracked Items).
    Emits a final snapshot through the max turn.
"""

import re

_KEY_RE = re.compile(r"^(?P<key>[^\n:][^\n]*?):[ \t]*$", re.MULTILINE)


def parse_tracked_items(section_text: str | None) -> dict | None:
    """Parse a tracked-items section body into ``{key: value}`` or ``None``.

    Parameters
    ----------
    section_text:
        The raw text of the section (after the ``----`` line), or ``None``.

    Returns
    -------
    ``dict`` mapping item names to their string values, or ``None`` if the
    section is absent or contains no key lines.
    """
    if section_text is None:
        return None

    matches = list(_KEY_RE.finditer(section_text))
    if not matches:
        return None

    result: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group("key")
        value_start = m.end() + 1  # skip the newline after the key line
        value_end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        raw_value = section_text[value_start:value_end]
        # Strip leading blank lines, then strip trailing whitespace.
        value = raw_value.lstrip("\n").rstrip()
        result[key] = value

    return result


def generate_snapshots(parsed_turns: list[dict]) -> list[dict]:
    """Build snapshot-on-change list over the tracked-state pair per turn.

    Parameters
    ----------
    parsed_turns:
        List of turn dicts, each with at least ``number``, ``trackedItems``
        (``dict | None``), ``hiddenTrackedItems`` (``dict | None``).
        Sorted ascending by ``number`` defensively.

    Returns
    -------
    List of snapshot dicts::

        [{"fromTurn": int, "toTurn": int,
          "trackedItems": dict | None, "hiddenTrackedItems": dict | None}]

    An empty ``parsed_turns`` list returns ``[]``.

    The header's ``Starting Tracked Items`` is NOT an input here.
    """
    if not parsed_turns:
        return []

    turns = sorted(parsed_turns, key=lambda t: t["number"])

    snapshots: list[dict] = []
    first = turns[0]
    prev_state = (first.get("trackedItems"), first.get("hiddenTrackedItems"))
    run_start = first["number"]
    prev_number = first["number"]

    for turn in turns[1:]:
        cur_state = (turn.get("trackedItems"), turn.get("hiddenTrackedItems"))
        if cur_state != prev_state:
            snapshots.append(
                {
                    "fromTurn": run_start,
                    "toTurn": prev_number,
                    "trackedItems": prev_state[0],
                    "hiddenTrackedItems": prev_state[1],
                }
            )
            run_start = turn["number"]
            prev_state = cur_state
        prev_number = turn["number"]

    # Always emit a final snapshot through the max turn.
    snapshots.append(
        {
            "fromTurn": run_start,
            "toTurn": turns[-1]["number"],
            "trackedItems": prev_state[0],
            "hiddenTrackedItems": prev_state[1],
        }
    )

    return snapshots
