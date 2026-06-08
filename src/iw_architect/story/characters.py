"""characters.py — build a character mention index from parsed turns.

Each character in ``character_list`` is described by a dict::

    {"name": str, "aliases": [str]}   # aliases is optional

For each character, scan every turn's source lines within its ``line_range``
for word-boundary matches of the name and any aliases (case-insensitive).

Returns ``(CharacterIndex | None, warnings)`` where
:class:`~iw_architect.story.models.CharacterIndex` has snake_case attributes.
Serialise with ``model_dump(by_alias=True)`` for camelCase JSON output.

If ``character_list`` is empty or None → return (None, []).
"""

from __future__ import annotations

import re

from iw_architect.story.models import CharacterEntry, CharacterIndex, CharacterMention


def _build_pattern(name: str, aliases: list[str]) -> re.Pattern:
    terms = [re.escape(t) for t in [name] + aliases if t]
    combined = "|".join(terms)
    return re.compile(rf"\b(?:{combined})\b", re.IGNORECASE)


def _build_context(text: str, start: int, end: int) -> str:
    """Context window around a match: up to 100 chars before ``start`` and 100
    after ``end``, each extended outward to a whole-word boundary so a word is
    never cut mid-token (the window may exceed 100 chars per side as a result).
    """
    left = max(0, start - 100)
    while left > 0 and not text[left - 1].isspace():
        left -= 1
    right = min(len(text), end + 100)
    while right < len(text) and not text[right].isspace():
        right += 1
    return text[left:right]


def index_characters(
    parsed_turns: list[dict],
    source_text: dict[str, str],
    character_list: list[dict],
) -> tuple[CharacterIndex | None, list[str]]:
    """Build a character mention index.

    Parameters
    ----------
    parsed_turns:
        List of turn dicts with at minimum ``number``, ``source``,
        ``line_range``.
    source_text:
        Mapping of absolute source path → full file text (LF-normalised).
    character_list:
        List of ``{"name": str, "aliases": [str]}`` dicts.

    Returns
    -------
    ``(CharacterIndex | None, warnings)``
    """
    if not character_list:
        return None, []

    warnings: list[str] = []
    # Mutable working structure: name → list of CharacterMention
    mentions_map: dict[str, list[CharacterMention]] = {}
    aliases_map: dict[str, list[str]] = {}
    patterns: dict[str, re.Pattern] = {}

    for char_def in character_list:
        name = char_def["name"]
        aliases = char_def.get("aliases", [])
        patterns[name] = _build_pattern(name, aliases)
        aliases_map[name] = aliases
        mentions_map[name] = []

    for turn in parsed_turns:
        turn_number = turn["number"]
        source = turn.get("source", "")
        line_range = turn.get("line_range")
        if not line_range or source not in source_text:
            continue
        start_line, end_line = line_range
        file_lines = source_text[source].split("\n")
        # line_range is 1-indexed inclusive; convert to 0-indexed slice.
        for idx in range(start_line - 1, min(end_line, len(file_lines))):
            line_text = file_lines[idx]
            line_number = idx + 1  # 1-indexed
            for char_def in character_list:
                name = char_def["name"]
                match = patterns[name].search(line_text)
                if match:
                    context = _build_context(line_text, match.start(), match.end())
                    mentions_map[name].append(
                        CharacterMention(turn=turn_number, line=line_number, context=context)
                    )

    total_mentions = sum(len(m) for m in mentions_map.values())

    # One warning per character that never matched (usually means the alias list
    # is off). Absence of mentions is normal, so this is informational only;
    # there is no `incomplete` flag — derive it from len(mentions) if needed.
    for name, m in mentions_map.items():
        if len(m) == 0:
            warnings.append(f"Character '{name}' had no mentions in the story.")

    characters = {
        name: CharacterEntry(aliases=aliases_map[name], mentions=mentions_map[name])
        for name in mentions_map
    }

    return (
        CharacterIndex(
            characters=characters,
            indexed_character_count=len(characters),
            total_mentions=total_mentions,
        ),
        warnings,
    )
