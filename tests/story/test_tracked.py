"""Tests for iw_architect.story.tracked."""

from iw_architect.story.models import Snapshot, Turn
from iw_architect.story.tracked import (
    generate_snapshots,
    parse_tracked_items,
    split_tracked_items,
)


class TestParseTrackedItems:
    def test_none_input_returns_none(self):
        assert parse_tracked_items(None) is None

    def test_empty_section_returns_none(self):
        # No key lines → None
        assert parse_tracked_items("   \n\n   ") is None

    def test_simple_key_value(self):
        result = parse_tracked_items("HP:\n10\n")
        assert result == {"HP": "10"}

    def test_empty_value_kept(self):
        result = parse_tracked_items("Notes:\n")
        assert result == {"Notes": ""}

    def test_multiple_keys(self):
        text = "Key Count:\n2\n\nNotes:\n"
        result = parse_tracked_items(text)
        assert result["Key Count"] == "2"
        assert result["Notes"] == ""

    def test_multiline_value(self):
        text = "Description:\nLine one.\nLine two.\n\nOther:\nval\n"
        result = parse_tracked_items(text)
        assert result["Description"] == "Line one.\nLine two."
        assert result["Other"] == "val"

    def test_xml_value_preserved(self):
        text = "Known Plants:\n<plants><plant name='x'/></plants>\n\nNotes:\n"
        result = parse_tracked_items(text)
        assert "<plants>" in result["Known Plants"]

    def test_colon_in_value_not_treated_as_key(self):
        # A line like "2: items" has a colon BUT not at end → not a key.
        text = "Items:\n2: swords\n3: shields\n"
        result = parse_tracked_items(text)
        assert "Items" in result
        assert "2" not in result

    def test_leading_blank_lines_stripped_from_value(self):
        text = "Key:\n\n\nvalue\n"
        result = parse_tracked_items(text)
        assert result["Key"] == "value"


def _make_turn(number: int, tracked_items=None, hidden_tracked_items=None) -> Turn:
    """Build a Turn model with minimal required fields for snapshot tests."""
    return Turn(
        number=number,
        action=None,
        outcome=None,
        secret_info=None,
        tracked_items=tracked_items,
        hidden_tracked_items=hidden_tracked_items,
        source="/fake/export.txt",
        line_range=(1, 1),
    )


class TestGenerateSnapshots:
    def _make_turns(self, states):
        """states: list of (number, tracked, hidden).
        Builds Turn models as generate_snapshots now requires.
        """
        return [_make_turn(n, t, h) for n, t, h in states]

    def test_empty_turns(self):
        assert generate_snapshots([]) == []

    def test_single_turn(self):
        turns = self._make_turns([(1, {"HP": "10"}, None)])
        result = generate_snapshots(turns)
        expected = [
            Snapshot(from_turn=1, to_turn=1, tracked_items={"HP": "10"}, hidden_tracked_items=None)
        ]
        assert result == expected

    def test_no_change_two_turns(self):
        turns = self._make_turns([(1, {"HP": "10"}, None), (2, {"HP": "10"}, None)])
        result = generate_snapshots(turns)
        expected = [
            Snapshot(from_turn=1, to_turn=2, tracked_items={"HP": "10"}, hidden_tracked_items=None)
        ]
        assert result == expected

    def test_spec_example_four_turns(self):
        """Spec §2 worked example: change at turn 3."""
        turns = self._make_turns(
            [
                (1, {"HP": "10"}, None),
                (2, {"HP": "10"}, None),
                (3, {"HP": "8"}, None),
                (4, {"HP": "8"}, None),
            ]
        )
        result = generate_snapshots(turns)
        assert result == [
            Snapshot(from_turn=1, to_turn=2, tracked_items={"HP": "10"}, hidden_tracked_items=None),
            Snapshot(from_turn=3, to_turn=4, tracked_items={"HP": "8"}, hidden_tracked_items=None),
        ]

    def test_change_every_turn(self):
        turns = self._make_turns(
            [(1, {"HP": "10"}, None), (2, {"HP": "9"}, None), (3, {"HP": "8"}, None)]
        )
        result = generate_snapshots(turns)
        assert len(result) == 3
        assert result[0] == Snapshot(
            from_turn=1, to_turn=1, tracked_items={"HP": "10"}, hidden_tracked_items=None
        )
        assert result[2].to_turn == 3

    def test_none_vs_empty_dict_differ(self):
        # None (absent) != {} (empty section)
        turns = self._make_turns([(1, None, None), (2, {}, None)])
        result = generate_snapshots(turns)
        assert len(result) == 2

    def test_sorted_defensively(self):
        # Out-of-order input should still produce correct output.
        states = [(3, {"HP": "8"}, None), (1, {"HP": "10"}, None), (2, {"HP": "10"}, None)]
        turns = self._make_turns(states)
        result = generate_snapshots(turns)
        assert result[0].from_turn == 1
        assert result[0].to_turn == 2

    def test_starting_tracked_items_not_involved(self):
        """Starting Tracked Items from the header is metadata only; not an input here."""
        turns = self._make_turns([(1, {"HP": "10"}, None), (2, {"HP": "10"}, None)])
        result = generate_snapshots(turns)
        # Should be a single snapshot, seeded from Turn 1's state.
        assert len(result) == 1
        assert result[0].from_turn == 1

    def test_hidden_tracked_change_triggers_snapshot(self):
        turns = self._make_turns(
            [
                (1, {"HP": "10"}, {"Secret": "A"}),
                (2, {"HP": "10"}, {"Secret": "B"}),
            ]
        )
        result = generate_snapshots(turns)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Multi-line YAML values (values whose own lines end in ":")
# ---------------------------------------------------------------------------

ABILITIES = (
    "Blink:\n"
    "  effect: Teleport a short distance.\n"
    "  cost: 1 mana\n"
    "  type: active\n"
    "Stoneskin:\n"
    "  effect: 'Skin hardens. Currently resists: blunt.'\n"
    "  cost: none\n"
    "  type: passive"
)
DEAD = "Cave Rat:\n- |-\n  First Fight, Level 1:\n  - Bitten once, then crushed.\n  - Day 1, dawn"
DEEDS = (
    "Crossed the old bridge: |-\n"
    "  - Took the long way round\n"
    "Found a hidden cache:\n"
    "- |-\n"
    "  - Under the third stone\n"
    "entries:\n"
    "- |-\n"
    "  Outwitted the toll keeper:\n"
    "    - Paid with a wooden coin"
)
YAML_SECTION = (
    "Level:\n1\n\nExp :\n0 / 10\n\nSpells:\n\n\n"
    f"Abilities:\n{ABILITIES}\n\nDead:\n{DEAD}\n\nDeeds:\n{DEEDS}\n\nNotes:\nStarted."
)
NAMES = ["Level", "Exp ", "Spells", "Abilities", "Dead", "Deeds", "Notes"]


class TestYamlValues:
    def test_known_names_anchor_boundaries(self):
        result = parse_tracked_items(YAML_SECTION, NAMES)
        assert list(result) == NAMES
        assert result["Abilities"] == ABILITIES
        assert result["Dead"] == DEAD
        assert result["Deeds"] == DEEDS
        assert result["Spells"] == ""
        assert result["Exp "] == "0 / 10"

    def test_fallback_without_names_matches(self):
        assert parse_tracked_items(YAML_SECTION) == parse_tracked_items(YAML_SECTION, NAMES)

    def test_no_key_starts_with_whitespace(self):
        for names in (None, NAMES):
            assert not any(k[:1].isspace() for k in parse_tracked_items(YAML_SECTION, names))
        # An indented key line after a blank line is still not an item.
        for names in (None, ["A"]):
            assert parse_tracked_items("A:\nx\n\n  Inner:\ny", names) == {"A": "x\n\n  Inner:\ny"}

    def test_trailing_space_in_name_is_significant(self):
        # "Exp" (no trailing space) does not match the line "Exp :".
        result = parse_tracked_items("Level:\n1\n\nExp :\n5", ["Level", "Exp"])
        assert result == {"Level": "1\n\nExp :\n5"}

    def test_unknown_name_line_reported(self):
        split = split_tracked_items("Level:\n1\n\nGold:\n5", ["Level"])
        assert split.items == {"Level": "1\n\nGold:\n5"}
        assert split.merged_unlisted == ["Gold"]
        assert split.leading_unlisted == split.fallback_unlisted == []

    def test_no_known_name_falls_back_and_reports_all(self):
        split = split_tracked_items("Gold:\n5\n\nSilver:\n2", ["Level"])
        assert split.items == {"Gold": "5", "Silver": "2"}
        assert split.fallback_unlisted == ["Gold", "Silver"]
        assert split.merged_unlisted == []

    def test_no_unknowns_without_names(self):
        split = split_tracked_items(YAML_SECTION)
        assert split.merged_unlisted == split.leading_unlisted == split.fallback_unlisted == []
        assert split.listed_inside_value == []

    def test_duplicate_known_name_prefers_boundary_line(self):
        # "Level:" nested inside Abilities' value must not start a new item.
        text = "Abilities:\nBlink:\nLevel:\n  3\n\nLevel:\n7"
        split = split_tracked_items(text, ["Abilities", "Level"])
        assert split.items == {"Abilities": "Blink:\nLevel:\n  3", "Level": "7"}
        assert split.listed_inside_value == ["Level"]

    def test_fallback_requires_blank_line_before_name(self):
        # Known limitation: without names, adjacent items with no blank line merge.
        assert parse_tracked_items("A:\n1\nB:\n2") == {"A": "1\nB:\n2"}

    def test_fallback_splits_value_with_blank_line(self):
        # Documented weakness: a blank line then a column-0 "Key:" inside a value.
        text = "Notes:\nline\n\nInner:\nmore"
        assert parse_tracked_items(text) == {"Notes": "line", "Inner": "more"}
        assert parse_tracked_items(text, ["Notes"]) == {"Notes": "line\n\nInner:\nmore"}

    def test_none_section_with_names(self):
        assert split_tracked_items(None, NAMES).items is None

    def test_leading_unlisted_item_kept(self):
        # The first item is not in the names: keep it as its own item, never drop it.
        split = split_tracked_items("A:\nfoo\n\nB:\nbar", ["B"])
        assert split.items == {"A": "foo", "B": "bar"}
        assert split.leading_unlisted == ["A"]
        assert split.merged_unlisted == split.fallback_unlisted == []

    def test_known_name_requires_boundary(self):
        # A listed name inside a value (no blank line before it) stays in the value.
        split = split_tracked_items("Plans:\nTime:\n  dawn", ["Plans", "Time"])
        assert split.items == {"Plans": "Time:\n  dawn"}
        assert split.listed_inside_value == ["Time"]

    def test_unseparated_items_merge_with_diagnostic(self):
        # Items not separated by blank lines merge in known-names mode too, but say so.
        split = split_tracked_items("Gold:\n5\nHP:\n10", ["Gold", "HP"])
        assert split.items == {"Gold": "5\nHP:\n10"}
        assert split.listed_inside_value == ["HP"]

    def test_repeated_fallback_key_does_not_overwrite(self):
        split = split_tracked_items("A:\n1\n\nA:\n2")
        assert split.items == {"A": "1\n\nA:\n2"}
        assert split.column0_key_lines_in_values == 1

    def test_column0_key_lines_counted(self):
        # Blink, Stoneskin, Cave Rat, Found a hidden cache, entries.
        assert split_tracked_items(YAML_SECTION).column0_key_lines_in_values == 5

    def test_unassigned_leading_text_counted(self):
        split = split_tracked_items("stray text\n\nA:\n1")
        assert split.items == {"A": "1"}
        assert split.unassigned_lines == 1
        none = split_tracked_items("just text")
        assert none.items is None
        assert none.unassigned_lines == 1
