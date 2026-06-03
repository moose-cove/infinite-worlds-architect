"""characters.py — build a character mention index from parsed turns.

Each character in ``character_list`` is described by a dict::

    {"name": str, "aliases": [str]}   # aliases is optional

For each character, scan every turn's source lines within its ``lineRange``
for word-boundary matches of the name and any aliases (case-insensitive).

Returns (character_index | None, warnings) where ``character_index`` is::

    {
        "characters": {
            "Name": {
                "name": "Name",
                "aliases": ["alt"],
                "mentions": [{"turn": int, "line": int, "context": str}],
            }
        },
        "indexed_character_count": int,
        "total_mentions": int,
        "incomplete": bool,  # True if any character had zero mentions
    }

``source_text`` is a dict mapping absolute source path → file content (str,
LF-normalised).  ``parse_turn_sections`` does not need to be called here —
the raw content lines are sufficient for context extraction.

If ``character_list`` is empty or None → return (None, []).
"""

import re


def _build_pattern(name: str, aliases: list[str]) -> re.Pattern:
    terms = [re.escape(t) for t in [name] + aliases if t]
    combined = "|".join(terms)
    return re.compile(rf"\b(?:{combined})\b", re.IGNORECASE)


def index_characters(
    parsed_turns: list[dict],
    source_text: dict[str, str],
    character_list: list[dict],
) -> tuple[dict | None, list[str]]:
    """Build a character mention index.

    Parameters
    ----------
    parsed_turns:
        List of turn dicts with at minimum ``number``, ``source``,
        ``lineRange``.
    source_text:
        Mapping of absolute source path → full file text (LF-normalised).
    character_list:
        List of ``{"name": str, "aliases": [str]}`` dicts.

    Returns
    -------
    ``(character_index | None, warnings)``
    """
    if not character_list:
        return None, []

    warnings: list[str] = []
    characters: dict[str, dict] = {}
    patterns: dict[str, re.Pattern] = {}

    for char_def in character_list:
        name = char_def["name"]
        aliases = char_def.get("aliases", [])
        patterns[name] = _build_pattern(name, aliases)
        characters[name] = {"name": name, "aliases": aliases, "mentions": []}

    for turn in parsed_turns:
        turn_number = turn["number"]
        source = turn.get("source", "")
        line_range = turn.get("lineRange")
        if not line_range or source not in source_text:
            continue
        start_line, end_line = line_range
        file_lines = source_text[source].split("\n")
        # lineRange is 1-indexed inclusive; convert to 0-indexed slice.
        for idx in range(start_line - 1, min(end_line, len(file_lines))):
            line_text = file_lines[idx]
            line_number = idx + 1  # 1-indexed
            for char_def in character_list:
                name = char_def["name"]
                if patterns[name].search(line_text):
                    context = line_text[:100]
                    characters[name]["mentions"].append(
                        {"turn": turn_number, "line": line_number, "context": context}
                    )

    total_mentions = sum(len(c["mentions"]) for c in characters.values())
    incomplete = any(len(c["mentions"]) == 0 for c in characters.values())

    if incomplete:
        missing = [n for n, c in characters.items() if len(c["mentions"]) == 0]
        warnings.append(f"Characters with no mentions: {', '.join(missing)}")

    return (
        {
            "characters": characters,
            "indexed_character_count": len(characters),
            "total_mentions": total_mentions,
            "incomplete": incomplete,
        },
        warnings,
    )
