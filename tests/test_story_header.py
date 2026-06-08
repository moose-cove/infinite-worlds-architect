"""Tests for iw_architect.story.header."""

from iw_architect.story.header import parse_header
from iw_architect.story.models import Metadata

FULL = (
    "== The Vault ==\n\n"
    "-- Story Background --\n\nA heist gone wrong.\n\n"
    "-- Character --\n\n"
    "Name\n----\nAda\n\n"
    "Background\n----------\nA retired safecracker.\n\n"
    "Skills\n------\nLockpicking, patience\n"
)


def test_returns_metadata_model():
    meta = parse_header(FULL)
    assert isinstance(meta, Metadata)


def test_full_header_fields():
    meta = parse_header(FULL)
    assert meta.title == "The Vault"
    assert meta.story_background == "A heist gone wrong."
    assert meta.character.name == "Ada"
    assert meta.character.background == "A retired safecracker."
    assert meta.character.skills == "Lockpicking, patience"
    assert meta.character.starting_tracked_items is None
    assert meta.objective is None


def test_full_header_serialises_camel_case():
    """Serialised form must use camelCase JSON keys."""
    meta = parse_header(FULL)
    data = meta.model_dump(by_alias=True)
    assert "storyBackground" in data
    assert "story_background" not in data
    assert "startingTrackedItems" in data["character"]
    assert "starting_tracked_items" not in data["character"]


def test_missing_story_background_is_none():
    no_bg = (
        "== Bare ==\n\n"
        "-- Character --\n\nName\n----\nX\n\nBackground\n----------\nY.\n\nSkills\n------\nZ\n"
    )
    meta = parse_header(no_bg)
    assert meta.story_background is None
    assert meta.title == "Bare"


def test_missing_title_is_none():
    meta = parse_header("-- Story Background --\n\nJust background.\n")
    assert meta.title is None
    assert meta.story_background == "Just background."


def test_missing_character_subfields_are_none():
    meta = parse_header("== Solo ==\n\n-- Story Background --\n\nbg\n")
    assert meta.character.name is None
    assert meta.character.background is None
    assert meta.character.skills is None
    assert meta.character.starting_tracked_items is None
