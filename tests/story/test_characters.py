"""Tests for iw_architect.story.characters."""

from iw_architect.story.characters import index_characters
from iw_architect.story.models import CharacterIndex, Turn


def _make_turns(entries):
    """entries: list of (number, source, line_range, raw_lines).
    Builds Turn models as index_characters now requires.
    """
    turns = []
    for number, source, line_range, _ in entries:
        turns.append(
            Turn(
                number=number,
                action=None,
                outcome=None,
                secret_info=None,
                tracked_items=None,
                hidden_tracked_items=None,
                source=source,
                line_range=tuple(line_range),
            )
        )
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


class TestSkipsTrackedItemSections:
    """Tracked Items / Hidden Tracked Items bodies must not produce mentions —
    a name embedded in a tracked-item label or value would otherwise register
    on every turn."""

    _LINES = [
        "-- Turn 2 --",  # 1
        "Action",  # 2
        "------",  # 3
        "Ada waves at Bob.",  # 4
        "Outcome",  # 5
        "-------",  # 6
        "Ada opens the door.",  # 7
        "Secret Information",  # 8
        "------------------",  # 9
        "Ada is hiding a key.",  # 10
        "Tracked Items",  # 11
        "-------------",  # 12
        "Ada's Mood: Anxious",  # 13
        "Bob: Wide-eyed, follower",  # 14
        "Hidden Tracked Items",  # 15
        "--------------------",  # 16
        "Ada's Hound Status:",  # 17
        "  implanter: Bob",  # 18
        "-- Turn 3 --",  # 19
        "Ada waits.",  # 20
        "Outcome",  # 21
        "-------",  # 22
        "Bob arrives.",  # 23
        "Tracked Items",  # 24
        "-------------",  # 25
        "Ada's Mood: Calm",  # 26
    ]

    def _index(self, line_range=(1, 26), turns=None):
        source = "/fake/export.txt"
        turn_defs = turns or [(2, source, list(line_range), self._LINES)]
        turns_models = _make_turns(turn_defs)
        src_text = {source: "\n".join(self._LINES)}
        char_index, _ = index_characters(
            turns_models,
            src_text,
            [{"name": "Ada", "aliases": []}, {"name": "Bob", "aliases": []}],
        )
        return char_index

    def test_tracked_item_lines_are_not_mentions(self):
        char_index = self._index(line_range=(1, 18))
        ada_lines = [m.line for m in char_index.characters["Ada"].mentions]
        bob_lines = [m.line for m in char_index.characters["Bob"].mentions]
        assert ada_lines == [4, 7, 10]
        assert bob_lines == [4]

    def test_action_outcome_secret_still_indexed(self):
        char_index = self._index(line_range=(1, 18))
        assert char_index.total_mentions == 4

    def test_turn_marker_resets_section(self):
        # Turn 3 starts inside what was Turn 2's Hidden Tracked Items section;
        # the marker must reset so Turn 3's pre-header text and Outcome count.
        source = "/fake/export.txt"
        turns = [(2, source, [1, 18], self._LINES), (3, source, [19, 26], self._LINES)]
        char_index = self._index(turns=turns)
        ada = [(m.turn, m.line) for m in char_index.characters["Ada"].mentions]
        bob = [(m.turn, m.line) for m in char_index.characters["Bob"].mentions]
        assert (3, 20) in ada
        assert (3, 23) in bob
        assert (3, 26) not in ada  # Turn 3 Tracked Items still skipped

    def test_header_and_rule_lines_never_yield_mentions(self):
        source = "/fake/export.txt"
        lines = ["-- Turn 1 --", "Ada", "-----", "Ada is here."]
        entries = [(1, source, [1, 4], lines)]
        char_index, _ = index_characters(
            _make_turns(entries),
            _make_source_text(entries),
            [{"name": "Ada", "aliases": []}],
        )
        # Line 2 is a section header (followed by a dash rule) — not a mention.
        assert [m.line for m in char_index.characters["Ada"].mentions] == [4]

    def test_turn_without_headers_scanned_in_full(self):
        source = "/fake/export.txt"
        lines = ["-- Turn 1 --", "Ada opens the door.", "Bob follows."]
        entries = [(1, source, [1, 3], lines)]
        char_index, _ = index_characters(
            _make_turns(entries),
            _make_source_text(entries),
            [{"name": "Ada", "aliases": []}, {"name": "Bob", "aliases": []}],
        )
        assert char_index.total_mentions == 2
