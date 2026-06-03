"""header.py — parse the header block of a story export.

Header format (spec §2):
- ``== Title ==``                              → ``title``
- ``-- Story Background --`` block            → ``storyBackground``
- ``-- Character --`` block with sub-sections:
    - ``Name\\n----``                          → ``character.name``
    - ``Background\\n----``                    → ``character.background``
    - ``Skills\\n----``                        → ``character.skills``
    - ``Starting Tracked Items\\n----``        → ``character.startingTrackedItems``
      (optional; parse with ``parse_tracked_items``; absent → ``None``)

The caller sets ``metadata["objective"] = None`` after calling this function;
this function does NOT produce an ``objective`` key.

Returns the ``metadata.json`` shape minus ``objective``.
"""

import re

from iw_architect.story.tracked import parse_tracked_items

_TITLE_RE = re.compile(r"^== (.+?) ==$", re.MULTILINE)
_BLOCK_RE = re.compile(r"^-- ([^\n]+?) --$", re.MULTILINE)
_SUBSECTION_RE = re.compile(r"^([^\n]+)\n-{4,}", re.MULTILINE)


def _extract_block(text: str, label: str) -> str | None:
    """Extract the body of a ``-- Label --`` top-level block."""
    matches = list(_BLOCK_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.group(1).strip().lower() == label.lower():
            body_start = m.end() + 1
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[body_start:body_end].strip()
    return None


def _extract_subsection(text: str, label: str) -> str | None:
    """Extract the body of a ``Name\\n----`` sub-section within a block."""
    matches = list(_SUBSECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.group(1).strip().lower() == label.lower():
            body_start = m.end() + 1
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[body_start:body_end].strip()
    return None


def parse_header(header_text: str) -> dict:
    """Parse the header block into a metadata dict (without ``objective``).

    Parameters
    ----------
    header_text:
        The raw text before the first ``-- Turn 1 --`` marker, CRLF-normalised.

    Returns
    -------
    dict with keys ``title``, ``storyBackground``, ``character`` (with sub-keys
    ``name``, ``background``, ``skills``, ``startingTrackedItems``).
    The caller must set ``objective = None``.
    """
    # Extract title (absent → None per §3 "string|null").
    title_match = _TITLE_RE.search(header_text)
    title = title_match.group(1).strip() if title_match else None

    # Extract story background (absent → None).
    story_background = _extract_block(header_text, "Story Background")

    # Extract character block. Keep "" here only so sub-section parsing is safe
    # when the block is absent — the individual sub-fields below stay None.
    char_block = _extract_block(header_text, "Character") or ""

    char_name = _extract_subsection(char_block, "Name")
    char_background = _extract_subsection(char_block, "Background")
    char_skills = _extract_subsection(char_block, "Skills")

    # Starting Tracked Items is optional.
    starting_raw = _extract_subsection(char_block, "Starting Tracked Items")
    starting_tracked = parse_tracked_items(starting_raw) if starting_raw is not None else None

    return {
        "title": title,
        "storyBackground": story_background,
        "character": {
            "name": char_name,
            "background": char_background,
            "skills": char_skills,
            "startingTrackedItems": starting_tracked,
        },
    }
