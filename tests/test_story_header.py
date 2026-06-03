"""Tests for iw_architect.story.header."""

from iw_architect.story.header import parse_header

FULL = (
    "== The Vault ==\n\n"
    "-- Story Background --\n\nA heist gone wrong.\n\n"
    "-- Character --\n\n"
    "Name\n----\nAda\n\n"
    "Background\n----------\nA retired safecracker.\n\n"
    "Skills\n------\nLockpicking, patience\n"
)


def test_full_header_fields():
    meta = parse_header(FULL)
    assert meta["title"] == "The Vault"
    assert meta["storyBackground"] == "A heist gone wrong."
    assert meta["character"]["name"] == "Ada"
    assert meta["character"]["background"] == "A retired safecracker."
    assert meta["character"]["skills"] == "Lockpicking, patience"
    assert meta["character"]["startingTrackedItems"] is None


def test_missing_story_background_is_none():
    no_bg = (
        "== Bare ==\n\n"
        "-- Character --\n\nName\n----\nX\n\nBackground\n----------\nY.\n\nSkills\n------\nZ\n"
    )
    meta = parse_header(no_bg)
    assert meta["storyBackground"] is None
    assert meta["title"] == "Bare"


def test_missing_title_is_none():
    meta = parse_header("-- Story Background --\n\nJust background.\n")
    assert meta["title"] is None
    assert meta["storyBackground"] == "Just background."


def test_missing_character_subfields_are_none():
    meta = parse_header("== Solo ==\n\n-- Story Background --\n\nbg\n")
    assert meta["character"]["name"] is None
    assert meta["character"]["background"] is None
    assert meta["character"]["skills"] is None
    assert meta["character"]["startingTrackedItems"] is None
