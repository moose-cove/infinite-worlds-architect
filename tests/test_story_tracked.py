"""Tests for iw_architect.story.tracked."""

from iw_architect.story.models import Snapshot
from iw_architect.story.tracked import generate_snapshots, parse_tracked_items


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


class TestGenerateSnapshots:
    def _make_turns(self, states):
        """states: list of (number, tracked, hidden).
        Uses snake_case keys as extract.py now produces.
        """
        return [{"number": n, "tracked_items": t, "hidden_tracked_items": h} for n, t, h in states]

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
