"""characters.py — build a character mention index from parsed turns.

Each character in ``character_list`` is described by a dict::

    {"name": str, "aliases": [str]}   # aliases is optional

For each character, scan every turn's source lines within its ``line_range``
for word-boundary matches of the name and any aliases (case-insensitive).

Lines that belong to a turn's ``Tracked Items`` / ``Hidden Tracked Items``
sections are **skipped**. Those sections are per-turn state tables, and a
tracked-item label or value that embeds a character's name (``Sage's Hound
Status:``, ``Kelsey Braddock: Wide-eyed, follower``) would otherwise register
as a "mention" on every single turn, drowning the narrative mentions the index
exists to surface. Section boundaries are detected the same way
:mod:`iw_architect.story.sections` detects them — a header line followed by a
line of four or more dashes — and a new ``-- Turn N --`` marker resets the
state so a turn that has no section headers at all is scanned in full.

Returns ``(CharacterIndex | None, warnings)`` where
:class:`~iw_architect.story.models.CharacterIndex` has snake_case attributes.
Serialise with ``model_dump(by_alias=True)`` for camelCase JSON output.

If ``character_list`` is empty or None → return (None, []).
"""

from __future__ import annotations

import re

from iw_architect.story.models import CharacterEntry, CharacterIndex, CharacterMention, Turn

#: Section headers (lower-cased) whose bodies are excluded from mention indexing.
_SKIPPED_SECTIONS: frozenset[str] = frozenset({"tracked items", "hidden tracked items"})

_TURN_MARKER = re.compile(r"^-- Turn \d+ --\s*$")
_DASH_RULE = re.compile(r"^-{4,}\s*$")


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


def _iter_indexable_lines(file_lines: list[str], start_line: int, end_line: int):
    """Yield ``(line_number, line_text)`` for the lines of one turn that should
    be scanned for character mentions.

    ``start_line`` / ``end_line`` are the turn's 1-indexed inclusive
    ``line_range``. Section headers (``Name`` followed by a ``----`` rule) and
    the rule lines themselves are never yielded; lines inside a section named
    in :data:`_SKIPPED_SECTIONS` are not yielded either. A ``-- Turn N --``
    marker resets the current section, so text before the first header of a
    turn — or a turn with no headers at all — is always scanned.
    """
    current_section: str | None = None
    last = min(end_line, len(file_lines))
    for idx in range(start_line - 1, last):
        line_text = file_lines[idx]
        if _TURN_MARKER.match(line_text):
            current_section = None
            continue
        if _DASH_RULE.match(line_text):
            continue
        if idx + 1 < len(file_lines) and _DASH_RULE.match(file_lines[idx + 1]):
            current_section = line_text.strip().lower()
            continue
        if current_section in _SKIPPED_SECTIONS:
            continue
        yield idx + 1, line_text


def index_characters(
    parsed_turns: list[Turn],
    source_text: dict[str, str],
    character_list: list[dict],
) -> tuple[CharacterIndex | None, list[str]]:
    """Build a character mention index.

    Parameters
    ----------
    parsed_turns:
        List of :class:`~iw_architect.story.models.Turn` models.
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
        turn_number = turn.number
        source = turn.source
        line_range = turn.line_range
        if source not in source_text:
            continue
        start_line, end_line = line_range
        file_lines = source_text[source].split("\n")
        for line_number, line_text in _iter_indexable_lines(file_lines, start_line, end_line):
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
