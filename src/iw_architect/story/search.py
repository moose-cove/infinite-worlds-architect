"""search.py — find the turns whose narrative text matches a keyword or regex.

Searches the parsed ``action`` / ``outcome`` / ``secretInfo`` sections stored in
``turn_index.json`` — not the raw export lines. Raw lines carry section headers
(``Outcome\\n-------``) that would match every turn, and searching the parsed
sections lets each match be attributed to its section. It also means search works
even if the source ``.txt`` files have moved since extraction (``turn_detail``
needs them in place; this does not).

Tracked-item sections are deliberately not searchable: their keys repeat on every
turn, so a term matching an item name would hit nearly every turn. Use
``tracked_state`` to follow tracked items instead.

Matching rules:

- ``keyword`` mode matches the query literally (escaped); ``regex`` mode takes
  Python ``re`` syntax. Both compile with ``MULTILINE``, plus ``IGNORECASE`` unless
  ``case_sensitive``.
- Patterns run on the third-party ``regex`` module (its default ``VERSION0`` is
  ``re``-compatible) rather than ``re``, because only ``regex`` can abandon a match:
  the whole search shares a ``SEARCH_TIMEOUT_SECONDS`` budget, so a pathological
  caller-supplied pattern returns an error instead of hanging the MCP server.
- ``whole_word`` (keyword mode only) requires the match not be adjacent to a word
  character — lookarounds rather than ``\\b``, so queries that begin or end with
  punctuation (``Mr.``) still match.
- Matches are non-overlapping (``finditer``) and scoped to one section; zero-length
  matches are skipped.

Snippets take ``SNIPPET_CONTEXT`` characters either side of the match, widen each
edge outward to a whole-word boundary (by at most ``SNIPPET_MAX_WIDEN`` extra
characters), never cross the section boundary, collapse whitespace runs to single
spaces, and mark cut edges with ``…``. A match longer than ``MAX_MATCH_CHARS`` is
shown truncated (with ``…``) in both ``match`` and the snippet. At most
``MAX_SNIPPETS_PER_TURN`` snippets are returned per turn, filled in section order;
``match_count`` stays exact.
"""

from __future__ import annotations

import os
import time

import regex

from iw_architect.story.models import SearchResult, SearchSnippet, TurnIndex, TurnSearchHit
from iw_architect.story.query import _read_json

# camelCase section name (the wire name) → Turn attribute, in search/report order.
SEARCHABLE_SECTIONS: dict[str, str] = {
    "action": "action",
    "outcome": "outcome",
    "secretInfo": "secret_info",
}
SEARCH_MODES = ("keyword", "regex")

SNIPPET_CONTEXT = 50
SNIPPET_MAX_WIDEN = 30
MAX_SNIPPETS_PER_TURN = 5
MAX_MATCH_CHARS = 200
SEARCH_TIMEOUT_SECONDS = 5.0


def _compile(query: str, mode: str, case_sensitive: bool, whole_word: bool) -> regex.Pattern:
    if mode not in SEARCH_MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {list(SEARCH_MODES)}")
    if not query.strip():
        raise ValueError("query must be a non-empty, non-whitespace string")
    if whole_word and mode == "regex":
        raise ValueError(
            "whole_word applies to keyword mode only; in regex mode write \\b (or "
            "lookarounds) into the pattern yourself"
        )

    pattern = regex.escape(query) if mode == "keyword" else query
    if whole_word:
        pattern = rf"(?<!\w){pattern}(?!\w)"
    flags = regex.MULTILINE | (0 if case_sensitive else regex.IGNORECASE)
    try:
        return regex.compile(pattern, flags)
    except regex.error as exc:
        raise ValueError(f"Invalid regex {query!r}: {exc}") from exc


def _resolve_sections(sections: list[str] | None) -> list[str]:
    if sections is None:
        return list(SEARCHABLE_SECTIONS)
    if not sections:
        raise ValueError("sections must name at least one section (omit it to search all)")
    unknown = [s for s in sections if s not in SEARCHABLE_SECTIONS]
    if unknown:
        raise ValueError(
            f"Unknown section(s) {unknown}; expected any of {list(SEARCHABLE_SECTIONS)}"
        )
    # De-duplicate and report in canonical order, whatever order the caller used.
    return [s for s in SEARCHABLE_SECTIONS if s in sections]


def _snippet(text: str, start: int, end: int) -> str:
    """Excerpt ``text`` around ``[start, end)``, widened to whole words.

    ``end`` should already be clamped to ``start + MAX_MATCH_CHARS``.
    """
    left = max(0, start - SNIPPET_CONTEXT)
    # Widen only when the cut lands mid-word (non-space on both sides of it).
    floor = max(0, left - SNIPPET_MAX_WIDEN)
    while left > floor and not text[left - 1].isspace() and not text[left].isspace():
        left -= 1

    right = min(len(text), end + SNIPPET_CONTEXT)
    ceiling = min(len(text), right + SNIPPET_MAX_WIDEN)
    while right < ceiling and not text[right - 1].isspace() and not text[right].isspace():
        right += 1

    excerpt = " ".join(text[left:right].split())
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{excerpt}{suffix}"


def search_turns(
    extraction_dir: str,
    query: str,
    mode: str = "keyword",
    case_sensitive: bool = False,
    whole_word: bool = False,
    sections: list[str] | None = None,
    include_snippets: bool = False,
) -> SearchResult:
    """Search every turn's narrative sections for ``query``.

    Parameters
    ----------
    extraction_dir:
        Directory containing ``turn_index.json`` (from ``extract_story_data``).
    query:
        The keyword (literal) or regex pattern.
    mode:
        ``"keyword"`` or ``"regex"``.
    case_sensitive:
        Match case exactly (default: case-insensitive).
    whole_word:
        Keyword mode only — reject matches adjacent to a word character.
    sections:
        Subset of ``action``, ``outcome``, ``secretInfo``; ``None`` searches all three.
    include_snippets:
        Attach up to ``MAX_SNIPPETS_PER_TURN`` context snippets to each hit.

    Returns
    -------
    A :class:`~iw_architect.story.models.SearchResult`; hits are sorted by turn
    number ascending and only turns with at least one match appear.

    Raises
    ------
    ValueError
        Unknown mode or section, empty query, invalid regex, empty ``sections``,
        ``whole_word`` combined with regex mode, a search exceeding
        ``SEARCH_TIMEOUT_SECONDS``, or a malformed ``turn_index.json``.
    FileNotFoundError
        If ``turn_index.json`` is missing from ``extraction_dir``.
    """
    pattern = _compile(query, mode, case_sensitive, whole_word)
    searched = _resolve_sections(sections)
    turn_index = TurnIndex.model_validate(
        _read_json(os.path.join(extraction_dir, "turn_index.json"))
    )
    deadline = time.monotonic() + SEARCH_TIMEOUT_SECONDS

    hits: list[TurnSearchHit] = []
    for turn in sorted(turn_index.turns, key=lambda t: t.number):
        section_counts: dict[str, int] = {}
        snippets: list[SearchSnippet] = []
        for section in searched:
            text = getattr(turn, SEARCHABLE_SECTIONS[section])
            if not text:
                continue
            count = 0
            try:
                matches = list(
                    pattern.finditer(text, timeout=max(0.0, deadline - time.monotonic()))
                )
            except TimeoutError as exc:
                raise ValueError(
                    f"Search timed out after {SEARCH_TIMEOUT_SECONDS:g}s — the regex is too "
                    "expensive (likely nested quantifiers); simplify the pattern"
                ) from exc
            for m in matches:
                if m.start() == m.end():
                    continue
                count += 1
                if include_snippets and len(snippets) < MAX_SNIPPETS_PER_TURN:
                    shown_end = min(m.end(), m.start() + MAX_MATCH_CHARS)
                    shown = text[m.start() : shown_end]
                    snippets.append(
                        SearchSnippet(
                            section=section,
                            match=shown if shown_end == m.end() else f"{shown}…",
                            text=_snippet(text, m.start(), shown_end),
                        )
                    )
            if count:
                section_counts[section] = count
        if section_counts:
            hits.append(
                TurnSearchHit(
                    turn=turn.number,
                    match_count=sum(section_counts.values()),
                    section_counts=section_counts,
                    snippets=snippets if include_snippets else None,
                )
            )

    return SearchResult(
        query=query,
        mode=mode,
        case_sensitive=case_sensitive,
        whole_word=whole_word,
        sections_searched=searched,
        turns_searched=len(turn_index.turns),
        matching_turn_count=len(hits),
        total_matches=sum(h.match_count for h in hits),
        results=hits,
    )
