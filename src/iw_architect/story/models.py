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
