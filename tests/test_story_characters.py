"""Tests for iw_architect.story.characters."""

from iw_architect.story.characters import index_characters
from iw_architect.story.models import CharacterIndex


def _make_turns(entries):
    """entries: list of (number, source, line_range, raw_lines).
    Uses snake_case keys as extract.py now produces.
    """
    turns = []
    for number, source, line_range, _ in entries:
        turns.append({"number": number, "source": source, "line_range": line_range})
    return turns


def _make_source_text(entries):
    """entries: list of (number, source, line_range, raw_lines)."""
    result = {}
    for _, source, _, raw_lines in entries:
        result[source] = "\n".join(raw_lines)
    return result


class TestIndexCharacters:
    def test_empty_character_list_returns_none(self):
        char_index, warnings = index_characters([], {}, [])
        assert char_index is None
        assert warnings == []

    def test_none_character_list_treated_as_empty(self):
        # character_list=None is handled in extract.py, but test empty list.
        char_index, warnings = index_characters([], {}, [])
        assert char_index is None

    def test_returns_character_index_model(self):
        source = "/fake/export.txt"
        lines = ["-- Turn 1 --", "Ada opens the door.", "She steps inside."]
        entries = [(1, source, [1, 3], lines)]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert isinstance(char_index, CharacterIndex)

    def test_single_character_found(self):
        source = "/fake/export.txt"
        lines = ["-- Turn 1 --", "Ada opens the door.", "She steps inside."]
        entries = [(1, source, [1, 3], lines)]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, warnings = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert char_index is not None
        assert len(char_index.characters["Ada"].mentions) >= 1

    def test_case_insensitive_match(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "ADA shouts."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert len(char_index.characters["Ada"].mentions) >= 1

    def test_word_boundary_match(self):
        source = "/fake/export.txt"
        # "Maddox" contains "ada" but "Ada" with word boundary should NOT match "Maddox".
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Maddox leaves."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert len(char_index.characters["Ada"].mentions) == 0

    def test_alias_match(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Ace picks the lock."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": ["Ace"]}])
        assert len(char_index.characters["Ada"].mentions) >= 1

    def test_context_extends_to_whole_word(self):
        # A long unbroken word adjacent to the match is included whole, even >100.
        source = "/fake/export.txt"
        long_word = "x" * 150
        line = f"Ada {long_word} end"
        entries = [(1, source, [1, 1], [line])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        ctx = char_index.characters["Ada"].mentions[0].context
        assert long_word in ctx  # whole word grabbed, not cut at 100

    def test_context_bounded_around_match(self):
        # ~100 chars before AND after the match — not the entire long line.
        source = "/fake/export.txt"
        far = "word " * 60  # 300 chars of short words on each side
        line = far + "Ada " + far
        entries = [(1, source, [1, 1], [line])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        ctx = char_index.characters["Ada"].mentions[0].context
        assert "Ada" in ctx
        assert len(ctx) < len(line)  # bounded — not the whole line
        # ~100 before + match + ~100 after, plus small word-boundary slack
        assert 150 <= len(ctx) <= 230

    def test_context_left_extends_to_whole_word(self):
        # A long unbroken word BEFORE the match is included whole (left boundary).
        source = "/fake/export.txt"
        long_word = "y" * 150
        line = f"start {long_word} Ada end"
        entries = [(1, source, [1, 1], [line])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        ctx = char_index.characters["Ada"].mentions[0].context
        assert long_word in ctx  # whole preceding word grabbed, not cut at 100

    def test_per_character_warning_when_no_mentions(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Nobody is here."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, warnings = index_characters(
            turns,
            src_text,
            [{"name": "Ada", "aliases": []}, {"name": "Bob", "aliases": []}],
        )
        # One warning per zero-mention character — no combined warning, no boolean.
        assert len(warnings) == 2
        assert any("Ada" in w for w in warnings)
        assert any("Bob" in w for w in warnings)
        assert not hasattr(char_index, "incomplete")

    def test_total_mentions_count(self):
        source = "/fake/export.txt"
        entries = [
            (
                1,
                source,
                [1, 4],
                [
                    "-- Turn 1 --",
                    "Ada opens the door.",
                    "Ada steps inside.",
                    "Bob watches.",
                ],
            )
        ]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(
            turns,
            src_text,
            [
                {"name": "Ada", "aliases": []},
                {"name": "Bob", "aliases": []},
            ],
        )
        assert char_index.total_mentions == 3
        assert char_index.indexed_character_count == 2

    def test_line_number_1_indexed(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 3], ["Ada is on line 1.", "Nothing.", "Ada again."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        lines = [m.line for m in char_index.characters["Ada"].mentions]
        assert 1 in lines  # line 1 is 1-indexed

    def test_character_index_serialises_camel_case(self):
        """Serialised form must use camelCase JSON keys."""
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Ada is here."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        data = char_index.model_dump(by_alias=True)
        assert "indexedCharacterCount" in data
        assert "indexed_character_count" not in data
        assert "totalMentions" in data
        assert "total_mentions" not in data
