"""models.py — Pydantic v2 models for story extraction output.

Casing convention:
- Python attributes (fields): snake_case
- Serialised / emitted JSON object keys: camelCase (via alias_generator)

Serialise with ``model.model_dump(by_alias=True, mode="json")``.
Parse with ``Model.model_validate(loaded_dict)`` (reads camelCase JSON keys;
``populate_by_name=True`` also accepts snake_case for internal construction).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )


# ---------------------------------------------------------------------------
# Primitive / shared sub-models
# ---------------------------------------------------------------------------


class TurnRange(_Base):
    """Inclusive min/max turn numbers in an extraction."""

    min: int
    max: int


class Source(_Base):
    """Provenance: a source file and the turn numbers it contributed."""

    path: str
    turns: list[int]


# ---------------------------------------------------------------------------
# turn_index.json
# ---------------------------------------------------------------------------


class Turn(_Base):
    """One parsed turn entry stored in ``turn_index.json``."""

    number: int
    action: str | None
    outcome: str | None
    secret_info: str | None
    tracked_items: dict[str, str] | None
    hidden_tracked_items: dict[str, str] | None
    source: str
    line_range: tuple[int, int]


class TurnIndex(_Base):
    """Contents of ``turn_index.json``."""

    turns: list[Turn]


# ---------------------------------------------------------------------------
# tracked_state.json
# ---------------------------------------------------------------------------


class Snapshot(_Base):
    """One snapshot entry in ``tracked_state.json``."""

    from_turn: int
    to_turn: int
    tracked_items: dict[str, str] | None
    hidden_tracked_items: dict[str, str] | None


class TrackedState(_Base):
    """Contents of ``tracked_state.json``."""

    snapshots: list[Snapshot]


# ---------------------------------------------------------------------------
# metadata.json
# ---------------------------------------------------------------------------


class Character(_Base):
    """Character sub-object within ``metadata.json``."""

    name: str | None
    background: str | None
    skills: str | None
    starting_tracked_items: dict[str, str] | None


class Metadata(_Base):
    """Contents of ``metadata.json``."""

    title: str | None
    story_background: str | None
    character: Character
    # Always None today (no Objective section in exports); typed str|None because
    # a sequel's objective may carry forward from the original world as a string.
    objective: str | None = None


# ---------------------------------------------------------------------------
# manifest.json  (ExtractionSummary + sources)
# ---------------------------------------------------------------------------


class ExtractionSummary(_Base):
    """The summary returned by ``extract_story_data`` (camelCase JSON keys)."""

    total_turns: int
    turn_range: TurnRange
    input_files_processed: int
    has_tracked_items: bool
    has_hidden_tracked_items: bool
    files_written: list[str]
    warnings: list[str]


class Manifest(ExtractionSummary):
    """Contents of ``manifest.json``: ExtractionSummary fields + sources."""

    sources: list[Source]


# ---------------------------------------------------------------------------
# character_index.json
# ---------------------------------------------------------------------------


class CharacterMention(_Base):
    """One mention of a character in a source file."""

    turn: int
    line: int
    context: str


class CharacterEntry(_Base):
    """Entry for one character in the character index."""

    aliases: list[str]
    mentions: list[CharacterMention]


class CharacterIndex(_Base):
    """Contents of ``character_index.json``."""

    characters: dict[str, CharacterEntry]
    indexed_character_count: int
    total_mentions: int


# ---------------------------------------------------------------------------
# turn_detail (query result — not a stored file)
# ---------------------------------------------------------------------------


class TurnDetail(_Base):
    """One entry in the ``turn_detail`` query result."""

    turn: int
    raw: str
    source: str


class TurnDetailResult(_Base):
    """Wrapper for the ``turn_detail`` query result (a list of TurnDetail)."""

    turn_detail: list[TurnDetail]


# ---------------------------------------------------------------------------
# search_turns (query result — not a stored file)
# ---------------------------------------------------------------------------


class SearchSnippet(_Base):
    """One match excerpt: the section it came from, the matched text, and context."""

    section: str
    match: str
    text: str


class TurnSearchHit(_Base):
    """One turn with at least one match.

    ``section_counts`` keys are camelCase section names (``secretInfo``) — dict keys
    are data, not model fields, so the alias generator does not touch them.
    ``snippets`` is ``None`` unless snippets were requested.
    """

    turn: int
    match_count: int
    section_counts: dict[str, int]
    snippets: list[SearchSnippet] | None = None


class SearchResult(_Base):
    """Result of ``search_turns``: echoed parameters, totals, and per-turn hits."""

    query: str
    mode: str
    case_sensitive: bool
    whole_word: bool
    sections_searched: list[str]
    turns_searched: int
    matching_turn_count: int
    total_matches: int
    results: list[TurnSearchHit]


# ---------------------------------------------------------------------------
# Internal pipeline models — produced/consumed within story/ (never written to
# disk, but use the same _Base so the casing convention holds if ever dumped).
# ---------------------------------------------------------------------------


class RawTurn(_Base):
    """A single turn split from the raw export, before section parsing."""

    number: int
    content: str
    source: str
    mtime: float


class CombineResult(_Base):
    """Result of merging one or more export files (``combine``)."""

    header: str
    turns: list[RawTurn]
    combined_text: str
    warnings: list[str]


class TrackedSplit(_Base):
    """Result of splitting one tracked-items section (``split_tracked_items``).

    ``items`` is the parsed ``{name: raw value}`` map (``None`` when the section
    is absent or has no name lines).  The other fields are diagnostics that
    ``extract_story_data`` turns into manifest warnings; each list holds raw keys
    (the line minus its trailing ``:``) in section order.
    """

    items: dict[str, str] | None
    #: Known-names mode: name-shaped lines not in the names, kept inside the
    #: value of the listed item above them.
    merged_unlisted: list[str] = []
    #: Known-names mode: name lines above the first listed item, not in the
    #: names, kept as their own items (blank-line rule applied to that prefix).
    leading_unlisted: list[str] = []
    #: Known-names mode: no listed name opened an item in this section, so the
    #: blank-line rule was used and these unlisted keys became items.
    fallback_unlisted: list[str] = []
    #: Known-names mode: lines naming a listed item that did not open an item
    #: (not at a blank-line boundary, or a repeat) and stayed inside a value.
    listed_inside_value: list[str] = []
    #: Column-0 ``Key:`` lines that ended up inside a value (any mode).
    column0_key_lines_in_values: int = 0
    #: Non-blank lines before the first name line, which no item could hold.
    unassigned_lines: int = 0


class TurnSections(_Base):
    """Raw section bodies parsed from one turn, before tracked-item parsing.

    ``tracked_items`` / ``hidden_tracked_items`` here are the raw section *text*
    (``str | None``), not the parsed ``dict`` maps used by :class:`Turn`.
    """

    action: str | None
    outcome: str | None
    secret_info: str | None
    tracked_items: str | None
    hidden_tracked_items: str | None
