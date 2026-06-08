"""sections.py — parse the sections within a single turn's body text.

Section name normalisation (spec §2):
- ``action``            → ``action``          (Turn 1 → ``None``)
- ``outcome``           → ``outcome``
- ``secret information``→ ``secret_info``
- ``tracked items``     → ``tracked_items``
- ``hidden tracked items`` → ``hidden_tracked_items``
- anything else         → ignored

Section header format: ``Name\n----`` (≥4 dashes).

Returns a :class:`~iw_architect.story.models.TurnSections` model (five
snake_case attributes); absent sections → ``None``. The ``tracked_items`` and
``hidden_tracked_items`` values are the raw section text strings
(``parse_tracked_items`` does the further parsing).
"""

import re

from iw_architect.story.models import TurnSections

_SECTION_HEADER = re.compile(r"^([^\n]+)\n-{4,}", re.MULTILINE)

_NORM: dict[str, str] = {
    "action": "action",
    "outcome": "outcome",
    "secret information": "secret_info",
    "tracked items": "tracked_items",
    "hidden tracked items": "hidden_tracked_items",
}


def _extract_sections(text: str) -> dict[str, str]:
    """Return a mapping of normalised-key → section-body for known sections."""
    result: dict[str, str] = {}
    matches = list(_SECTION_HEADER.finditer(text))
    for i, m in enumerate(matches):
        raw_name = m.group(1).strip()
        key = _NORM.get(raw_name.lower())
        if key is None:
            continue
        body_start = m.end() + 1  # skip newline after the dashes line
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip("\n")
        result[key] = body
    return result


def parse_turn_sections(turn_content: str, turn_number: int) -> TurnSections:
    """Parse a turn's body into its five canonical sections.

    Parameters
    ----------
    turn_content:
        The raw text of the turn after its ``-- Turn N --`` marker line, with
        CRLF already normalised to LF by ``combine``.
    turn_number:
        The turn number; used to enforce ``action is None`` for Turn 1.

    Returns
    -------
    A :class:`~iw_architect.story.models.TurnSections` (snake_case attributes
    ``action``, ``outcome``, ``secret_info``, ``tracked_items``,
    ``hidden_tracked_items``).  Any absent section is ``None``;
    ``tracked_items`` / ``hidden_tracked_items`` are raw strings for further
    parsing by ``parse_tracked_items``.
    """
    sections = _extract_sections(turn_content)

    action = sections.get("action")
    if turn_number == 1:
        action = None
    elif action is not None:
        action = action.strip()
        if not action:
            action = None

    outcome = sections.get("outcome")
    if outcome is not None:
        outcome = outcome.strip()
        if not outcome:
            outcome = None

    secret_info = sections.get("secret_info")
    if secret_info is not None:
        secret_info = secret_info.strip()
        if not secret_info:
            secret_info = None

    return TurnSections(
        action=action,
        outcome=outcome,
        secret_info=secret_info,
        tracked_items=sections.get("tracked_items"),
        hidden_tracked_items=sections.get("hidden_tracked_items"),
    )
