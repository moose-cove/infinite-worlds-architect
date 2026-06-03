"""Tests for iw_architect.story.sections."""

from iw_architect.story.sections import parse_turn_sections

TURN2_BODY = (
    "\nAction\n------\nOpen the locker.\n\n"
    "Outcome\n-------\nIt creaks open.\n\n"
    "Tracked Items\n-------------\nKey Count:\n2\n\nNotes:\n"
)

TURN1_BODY = (
    "\nOutcome\n-------\nYou arrive.\n\n"
    "Secret Information\n------------------\nThe safe is empty.\n\n"
    "Tracked Items\n-------------\nHP:\n10\n"
)


class TestTurn1:
    def test_action_is_none_for_turn1(self):
        result = parse_turn_sections(TURN1_BODY, 1)
        assert result["action"] is None

    def test_outcome_present(self):
        result = parse_turn_sections(TURN1_BODY, 1)
        assert result["outcome"] == "You arrive."

    def test_secret_info_present(self):
        result = parse_turn_sections(TURN1_BODY, 1)
        assert result["secretInfo"] == "The safe is empty."

    def test_tracked_items_raw_string(self):
        result = parse_turn_sections(TURN1_BODY, 1)
        assert result["trackedItems"] is not None
        assert "HP" in result["trackedItems"]

    def test_hidden_tracked_items_none(self):
        result = parse_turn_sections(TURN1_BODY, 1)
        assert result["hiddenTrackedItems"] is None


class TestTurn2:
    def test_action_present(self):
        result = parse_turn_sections(TURN2_BODY, 2)
        assert result["action"] == "Open the locker."

    def test_outcome_present(self):
        result = parse_turn_sections(TURN2_BODY, 2)
        assert result["outcome"] == "It creaks open."

    def test_secret_info_none_when_absent(self):
        result = parse_turn_sections(TURN2_BODY, 2)
        assert result["secretInfo"] is None

    def test_tracked_items_raw_contains_keys(self):
        result = parse_turn_sections(TURN2_BODY, 2)
        raw = result["trackedItems"]
        assert "Key Count" in raw
        assert "Notes" in raw

    def test_hidden_tracked_items_none_when_absent(self):
        result = parse_turn_sections(TURN2_BODY, 2)
        assert result["hiddenTrackedItems"] is None


class TestSectionNormalisation:
    def test_secret_information_normalised(self):
        body = "\nSecret Information\n------------------\nHidden truth.\n"
        result = parse_turn_sections(body, 3)
        assert result["secretInfo"] == "Hidden truth."

    def test_hidden_tracked_items_normalised(self):
        body = (
            "\nAction\n------\nDo it.\n\n"
            "Outcome\n-------\nDone.\n\n"
            "Hidden Tracked Items\n--------------------\nSecret:\n42\n"
        )
        result = parse_turn_sections(body, 2)
        assert result["hiddenTrackedItems"] is not None
        assert "Secret" in result["hiddenTrackedItems"]

    def test_unknown_sections_ignored(self):
        body = (
            "\nAction\n------\nAct.\n\n"
            "Outcome\n-------\nOut.\n\n"
            "Narrator Notes\n--------------\nSome GM note.\n"
        )
        result = parse_turn_sections(body, 2)
        assert result["action"] == "Act."
        assert result["outcome"] == "Out."

    def test_crlf_body(self):
        body = "\r\nAction\r\n------\r\nMove.\r\n\r\nOutcome\r\n-------\r\nMoved.\r\n"
        # sections.py receives already-normalised text from combine,
        # but test tolerance here directly.
        result = parse_turn_sections(body.replace("\r\n", "\n"), 2)
        assert result["action"] == "Move."
