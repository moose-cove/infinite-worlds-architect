"""Tests for iw_architect.story.characters."""

from iw_architect.story.characters import index_characters


def _make_turns(entries):
    """entries: list of (number, source, line_range, raw_lines)."""
    turns = []
    for number, source, line_range, _ in entries:
        turns.append({"number": number, "source": source, "lineRange": line_range})
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

    def test_single_character_found(self):
        source = "/fake/export.txt"
        lines = ["-- Turn 1 --", "Ada opens the door.", "She steps inside."]
        entries = [(1, source, [1, 3], lines)]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, warnings = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert char_index is not None
        assert len(char_index["characters"]["Ada"]["mentions"]) >= 1

    def test_case_insensitive_match(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "ADA shouts."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert len(char_index["characters"]["Ada"]["mentions"]) >= 1

    def test_word_boundary_match(self):
        source = "/fake/export.txt"
        # "Maddox" contains "ada" but "Ada" with word boundary should NOT match "Maddox".
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Maddox leaves."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert len(char_index["characters"]["Ada"]["mentions"]) == 0

    def test_alias_match(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Ace picks the lock."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": ["Ace"]}])
        assert len(char_index["characters"]["Ada"]["mentions"]) >= 1

    def test_context_truncated_at_100(self):
        source = "/fake/export.txt"
        long_line = "Ada " + "x" * 200
        entries = [(1, source, [1, 2], ["-- Turn 1 --", long_line])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        for mention in char_index["characters"]["Ada"]["mentions"]:
            assert len(mention["context"]) <= 100

    def test_incomplete_flag_when_no_mentions(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 2], ["-- Turn 1 --", "Nobody is here."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, warnings = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        assert char_index["incomplete"] is True
        assert len(warnings) >= 1

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
        assert char_index["total_mentions"] == 3
        assert char_index["indexed_character_count"] == 2

    def test_line_number_1_indexed(self):
        source = "/fake/export.txt"
        entries = [(1, source, [1, 3], ["Ada is on line 1.", "Nothing.", "Ada again."])]
        turns = _make_turns(entries)
        src_text = _make_source_text(entries)
        char_index, _ = index_characters(turns, src_text, [{"name": "Ada", "aliases": []}])
        lines = [m["line"] for m in char_index["characters"]["Ada"]["mentions"]]
        assert 1 in lines  # line 1 is 1-indexed
