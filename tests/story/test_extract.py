"""Tests for iw_architect.story.extract."""

import json
import os

import pytest

from iw_architect.story.extract import _tracked_item_warnings, extract_story_data
from iw_architect.story.models import ExtractionSummary, Turn

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def fixture(name: str) -> str:
    return os.path.join(FIXTURES, name)


class TestExtractBasic:
    def test_returns_extraction_summary_model(self, tmp_path):
        summary = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert isinstance(summary, ExtractionSummary)

    def test_summary_snake_attributes(self, tmp_path):
        summary = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        # Access via snake_case attributes.
        assert summary.total_turns == 5
        assert summary.turn_range.min == 1
        assert summary.turn_range.max == 5
        assert summary.input_files_processed == 1
        assert summary.has_tracked_items is True
        assert summary.has_hidden_tracked_items is True

    def test_summary_serialises_camel_case(self, tmp_path):
        """model_dump(by_alias=True) must emit camelCase keys only, NO snake leakage."""
        summary = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        data = summary.model_dump(by_alias=True)
        assert set(data) == {
            "totalTurns",
            "turnRange",
            "inputFilesProcessed",
            "hasTrackedItems",
            "hasHiddenTrackedItems",
            "filesWritten",
            "warnings",
        }
        assert "total_turns" not in data
        assert "turnRange" in data
        assert data["turnRange"] == {"min": 1, "max": 5}

    def test_manifest_json_has_camel_total_turns_and_sources(self, tmp_path):
        """manifest.json on disk is pure camelCase; no snake total_turns key."""
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        # Pure camelCase — totalTurns present, snake total_turns absent.
        assert manifest["totalTurns"] == 5
        assert "total_turns" not in manifest
        assert manifest["filesWritten"]  # camelCase mirror present
        assert isinstance(manifest["sources"], list)
        assert manifest["sources"][0]["turns"] == [1, 2, 3, 4, 5]
        assert os.path.isabs(manifest["sources"][0]["path"])

    def test_manifest_json_written(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert (tmp_path / "manifest.json").exists()

    def test_metadata_json_written(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert (tmp_path / "metadata.json").exists()

    def test_turn_index_json_written(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert (tmp_path / "turn_index.json").exists()

    def test_tracked_state_written_when_tracked_items_present(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert (tmp_path / "tracked_state.json").exists()

    def test_character_index_not_written_without_list(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert not (tmp_path / "character_index.json").exists()

    def test_five_files_with_character_list(self, tmp_path):
        summary = extract_story_data(
            [fixture("story_export_single_5turn.txt")],
            str(tmp_path),
            character_list=[{"name": "Petra Voss", "aliases": []}],
        )
        assert (tmp_path / "character_index.json").exists()
        assert len(summary.files_written) == 5

    def test_four_files_no_character_list(self, tmp_path):
        summary = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert len(summary.files_written) == 4

    def test_three_files_no_tracked_no_character(self, tmp_path):
        # no_hidden.txt has tracked items but no hidden; tracked_state should still be written
        # since tracked items ARE present. Use a file with no tracked items at all.
        src = tmp_path / "notracks.txt"
        char_header = (
            "== No Tracks ==\n\n-- Character --\n\n"
            "Name\n----\nX\n\nBackground\n----------\nNone.\n\nSkills\n------\nNone.\n\n"
        )
        src.write_text(
            char_header
            + "-- Turn 1 --\n\nOutcome\n-------\nStart.\n\n"
            + "-- Turn 2 --\n\nAction\n------\nGo.\n\nOutcome\n-------\nGone.\n\n",
            encoding="utf-8",
        )
        summary = extract_story_data([str(src)], str(tmp_path / "out"))
        assert len(summary.files_written) == 3
        assert not (tmp_path / "out" / "tracked_state.json").exists()


class TestExtractIdempotent:
    def test_rerun_overwrites(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        m_path = tmp_path / "manifest.json"
        with open(m_path) as f:
            original = json.load(f)
        # Second run.
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(m_path) as f:
            second = json.load(f)
        assert original["totalTurns"] == second["totalTurns"]


class TestExtractMetadata:
    def test_metadata_title(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert meta["title"] == "The Iron Gate"

    def test_metadata_objective_none(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert meta["objective"] is None

    def test_metadata_story_background_camel_case(self, tmp_path):
        """metadata.json must use camelCase: storyBackground not story_background."""
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert "storyBackground" in meta
        assert "story_background" not in meta

    def test_metadata_character_name(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert meta["character"]["name"] == "Petra Voss"

    def test_metadata_starting_tracked_items_camel_case(self, tmp_path):
        """character sub-object uses startingTrackedItems (camelCase)."""
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert "startingTrackedItems" in meta["character"]
        assert "starting_tracked_items" not in meta["character"]
        # single_5turn.txt has Starting Tracked Items.
        assert meta["character"]["startingTrackedItems"] is not None

    def test_metadata_no_starting_tracked_items(self, tmp_path):
        extract_story_data([fixture("story_export_no_hidden.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert meta["character"]["startingTrackedItems"] is None


class TestExtractTurnIndex:
    def test_turn1_action_none(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "turn_index.json") as f:
            idx = json.load(f)
        turn1 = next(t for t in idx["turns"] if t["number"] == 1)
        assert turn1["action"] is None

    def test_turn2_has_action(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "turn_index.json") as f:
            idx = json.load(f)
        turn2 = next(t for t in idx["turns"] if t["number"] == 2)
        assert turn2["action"] is not None

    def test_turn_index_camel_case_keys(self, tmp_path):
        """turn_index.json entries must use camelCase for multi-word fields."""
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "turn_index.json") as f:
            idx = json.load(f)
        for turn in idx["turns"]:
            assert "secretInfo" in turn
            assert "secret_info" not in turn
            assert "trackedItems" in turn
            assert "tracked_items" not in turn
            assert "hiddenTrackedItems" in turn
            assert "hidden_tracked_items" not in turn
            assert "lineRange" in turn
            assert "line_range" not in turn

    def test_line_range_is_list_of_two_ints(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "turn_index.json") as f:
            idx = json.load(f)
        for turn in idx["turns"]:
            lr = turn["lineRange"]
            assert isinstance(lr, list)
            assert len(lr) == 2
            assert lr[0] >= 1
            assert lr[1] >= lr[0]

    def test_source_is_absolute_path(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "turn_index.json") as f:
            idx = json.load(f)
        for turn in idx["turns"]:
            assert os.path.isabs(turn["source"])

    def test_raises_on_no_turn1(self, tmp_path):
        with pytest.raises(ValueError, match="No Turn 1"):
            extract_story_data([fixture("story_export_no_turn1.txt")], str(tmp_path))


class TestExtractTrackedState:
    def test_snapshots_present(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "tracked_state.json") as f:
            ts = json.load(f)
        assert "snapshots" in ts
        assert len(ts["snapshots"]) >= 1

    def test_tracked_state_camel_case_keys(self, tmp_path):
        """tracked_state.json snapshot entries must use camelCase."""
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "tracked_state.json") as f:
            ts = json.load(f)
        for snap in ts["snapshots"]:
            assert "fromTurn" in snap
            assert "from_turn" not in snap
            assert "toTurn" in snap
            assert "to_turn" not in snap
            assert "trackedItems" in snap
            assert "tracked_items" not in snap
            assert "hiddenTrackedItems" in snap
            assert "hidden_tracked_items" not in snap

    def test_no_hidden_file_tracked_state_written(self, tmp_path):
        extract_story_data([fixture("story_export_no_hidden.txt")], str(tmp_path))
        assert (tmp_path / "tracked_state.json").exists()


class TestExtractCharacterIndex:
    def test_character_index_camel_case_keys(self, tmp_path):
        """character_index.json must use camelCase for count fields."""
        extract_story_data(
            [fixture("story_export_single_5turn.txt")],
            str(tmp_path),
            character_list=[{"name": "Petra Voss", "aliases": ["Petra"]}],
        )
        with open(tmp_path / "character_index.json") as f:
            ci = json.load(f)
        assert "indexedCharacterCount" in ci
        assert "indexed_character_count" not in ci
        assert "totalMentions" in ci
        assert "total_mentions" not in ci


class TestExtractCreatesDir:
    def test_creates_extraction_dir_if_not_exists(self, tmp_path):
        out = tmp_path / "new_dir"
        assert not out.exists()
        extract_story_data([fixture("story_export_single_5turn.txt")], str(out))
        assert out.exists()


# ---------------------------------------------------------------------------
# Multi-line YAML tracked items (story_export_yaml_tracked.txt)
# ---------------------------------------------------------------------------

YAML_NAMES = ["Level", "Exp ", "Spells", "Abilities", "Dead", "Deeds", "Notes", "Secret Plans"]
VISIBLE = YAML_NAMES[:-1]
ABILITIES_T1 = (
    "Blink:\n"
    "  effect: Teleport a short distance.\n"
    "  cost: 1 mana\n"
    "  type: active\n"
    "Stoneskin:\n"
    "  effect: 'Skin hardens. Currently resists: blunt.'\n"
    "  cost: none\n"
    "  type: passive"
)
DEAD_T2 = (
    "Cave Rat:\n"
    "- |-\n"
    "  First Fight, Level 1:\n"
    "  - Bitten once, then crushed.\n"
    "  - Day 1, dawn\n"
    "Bog Goblin (Level 2): Drowned in the marsh."
)
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


def _turns(extraction_dir) -> list[dict]:
    with open(os.path.join(extraction_dir, "turn_index.json")) as f:
        return json.load(f)["turns"]


class TestYamlTrackedItems:
    def test_names_give_exact_key_set_every_turn(self, tmp_path):
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=YAML_NAMES
        )
        assert summary.warnings == []
        for turn in _turns(tmp_path):
            assert list(turn["trackedItems"]) == VISIBLE
            assert list(turn["hiddenTrackedItems"]) == ["Secret Plans"]

    def test_values_are_raw_source_blocks(self, tmp_path):
        extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=YAML_NAMES
        )
        turns = _turns(tmp_path)
        assert turns[0]["trackedItems"]["Abilities"] == ABILITIES_T1
        assert turns[1]["trackedItems"]["Dead"] == DEAD_T2
        assert turns[0]["trackedItems"]["Deeds"] == DEEDS
        assert turns[0]["trackedItems"]["Spells"] == ""
        assert turns[0]["hiddenTrackedItems"]["Secret Plans"].startswith("Phase:\n  current:")

    def test_fallback_matches_named_result(self, tmp_path):
        extract_story_data(
            [fixture("story_export_yaml_tracked.txt")],
            str(tmp_path / "a"),
            tracked_item_names=YAML_NAMES,
        )
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path / "b")
        )
        # Only the aggregated "column-0 keys kept inside values" note (YAML map keys).
        assert len(summary.warnings) == 1
        assert "19 column-0 'Key:' line(s) on 3 turn(s)" in summary.warnings[0]
        assert _turns(tmp_path / "a") == _turns(tmp_path / "b")

    def test_no_key_starts_with_whitespace(self, tmp_path):
        extract_story_data([fixture("story_export_yaml_tracked.txt")], str(tmp_path))
        for turn in _turns(tmp_path):
            assert not any(k[:1].isspace() for k in turn["trackedItems"])

    def test_unknown_name_line_warns(self, tmp_path):
        names = [n for n in YAML_NAMES if n != "Notes"]
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=names
        )
        assert summary.warnings == [
            "Tracked Items: line 'Notes:' is not in tracked_item_names, so it was kept inside "
            "the value of the listed item above it (turns 1, 2, 3). Add the name if it is a "
            "real item."
        ]
        assert "Notes" not in _turns(tmp_path)[0]["trackedItems"]
        assert _turns(tmp_path)[0]["trackedItems"]["Deeds"].endswith("Notes:\nStarted the journey.")

    def test_leading_unlisted_item_kept_and_warned(self, tmp_path):
        names = [n for n in YAML_NAMES if n != "Level"]
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=names
        )
        assert [t["trackedItems"]["Level"] for t in _turns(tmp_path)] == ["1", "1", "2"]
        with open(tmp_path / "tracked_state.json") as fh:
            snaps = json.load(fh)["snapshots"]
        assert all("Level" in s["trackedItems"] for s in snaps)
        assert summary.warnings == [
            "Tracked Items: line 'Level:' comes before the first listed item and is not in "
            "tracked_item_names; it was kept as its own item (turns 1, 2, 3). Add the name if "
            "it is a real item."
        ]

    def test_section_with_no_listed_name_warns_truthfully(self, tmp_path):
        names = [n for n in YAML_NAMES if n != "Secret Plans"]
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=names
        )
        assert list(_turns(tmp_path)[0]["hiddenTrackedItems"]) == ["Secret Plans"]
        assert len(summary.warnings) == 1
        assert summary.warnings[0].startswith(
            "Hidden Tracked Items: no line matched a name in tracked_item_names, so the "
            "blank-line rule was used and line 'Secret Plans:' became an item (turns 1, 2, 3)."
        )
        assert "kept inside" not in summary.warnings[0]
        # A partial name list is as likely as a wrong one: the warning must cover both.
        assert "missing the names of the items in this section" in summary.warnings[0]
        assert "do not belong to the world" in summary.warnings[0]

    def test_never_matched_name_warns(self, tmp_path):
        summary = extract_story_data(
            [fixture("story_export_yaml_tracked.txt")],
            str(tmp_path),
            tracked_item_names=[*YAML_NAMES, "Exp"],
        )
        assert summary.warnings == [
            "tracked_item_names never matched a name line in any turn: 'Exp'. Check the "
            "names against the export (matching is exact, trailing spaces included)."
        ]

    def test_keyset_change_warns_without_names(self, tmp_path):
        src = tmp_path / "export.txt"
        src.write_text(
            "== T ==\n\n-- Turn 1 --\n\nOutcome\n-------\nA.\n\n"
            "Tracked Items\n-------------\nNotes:\nx\n\n"
            "-- Turn 2 --\n\nAction\n------\nGo.\n\nOutcome\n-------\nB.\n\n"
            "Tracked Items\n-------------\nNotes:\nx\n\nStray:\ny\n"
        )
        summary = extract_story_data([str(src)], str(tmp_path / "out"))
        assert len(summary.warnings) == 1
        assert "between turns 1 and 2" in summary.warnings[0]
        assert "added: ['Stray']" in summary.warnings[0]
        assert "tracked_item_names" in summary.warnings[0]

    def test_keyset_change_warnings_capped(self, tmp_path):
        parts = ["== T ==\n"]
        for n in range(1, 15):
            action = "" if n == 1 else "Action\n------\nGo.\n\n"
            extra = "\nStray:\ny\n" if n % 2 else ""
            parts.append(
                f"\n-- Turn {n} --\n\n{action}Outcome\n-------\nA.\n\n"
                f"Tracked Items\n-------------\nNotes:\nx\n{extra}"
            )
        src = tmp_path / "export.txt"
        src.write_text("".join(parts))
        summary = extract_story_data([str(src)], str(tmp_path / "out"))
        assert len(summary.warnings) == 11
        assert summary.warnings[-1].startswith("… 3 more tracked-item key-set changes")


def _export(tmp_path, *turn_sections: tuple[str, str | None]) -> str:
    """Write a minimal export whose turns have the given (tracked, hidden) section bodies."""
    parts = ["== T ==\n"]
    for n, (tracked, hidden) in enumerate(turn_sections, start=1):
        action = "" if n == 1 else "Action\n------\nGo.\n\n"
        body = f"\n-- Turn {n} --\n\n{action}Outcome\n-------\nA.\n\n"
        body += f"Tracked Items\n-------------\n{tracked}\n\n"
        if hidden is not None:
            body += f"Hidden Tracked Items\n--------------------\n{hidden}\n\n"
        parts.append(body)
    path = tmp_path / "export.txt"
    path.write_text("".join(parts))
    return str(path)


def _turn(number: int, tracked: dict | None, hidden: dict | None = None) -> Turn:
    return Turn(
        number=number,
        action=None,
        outcome=None,
        secret_info=None,
        tracked_items=tracked,
        hidden_tracked_items=hidden,
        source="/fake.txt",
        line_range=(1, 1),
    )


class TestTrackedItemDiagnostics:
    def test_names_apply_to_hidden_section(self, tmp_path):
        src = _export(tmp_path, ("Level:\n1", "Plans:\nstep one\n\nBackup:\nyes"))
        extract_story_data([src], str(tmp_path / "named"), tracked_item_names=["Level", "Plans"])
        extract_story_data([src], str(tmp_path / "bare"))
        assert _turns(tmp_path / "named")[0]["hiddenTrackedItems"] == {
            "Plans": "step one\n\nBackup:\nyes"
        }
        assert _turns(tmp_path / "bare")[0]["hiddenTrackedItems"] == {
            "Plans": "step one",
            "Backup": "yes",
        }

    def test_listed_name_inside_value_not_split(self, tmp_path):
        src = _export(tmp_path, ("Time:\nnoon", "Plans:\nTime:\n  dawn"))
        summary = extract_story_data(
            [src], str(tmp_path / "out"), tracked_item_names=["Time", "Plans"]
        )
        turn = _turns(tmp_path / "out")[0]
        assert turn["hiddenTrackedItems"] == {"Plans": "Time:\n  dawn"}
        assert turn["trackedItems"] == {"Time": "noon"}
        assert summary.warnings == [
            "Hidden Tracked Items: line 'Time:' matches a name in tracked_item_names but does "
            "not open the section or follow a blank line, or repeats an earlier name line, so "
            "it was kept inside the value it sits in (turns 1)."
        ]

    def test_unseparated_items_warn_once_without_names(self, tmp_path):
        src = _export(tmp_path, ("Gold:\n5\nHP:\n10", None), ("Gold:\n4\nHP:\n10", None))
        summary = extract_story_data([src], str(tmp_path / "out"))
        assert _turns(tmp_path / "out")[0]["trackedItems"] == {"Gold": "5\nHP:\n10"}
        assert len(summary.warnings) == 1
        assert summary.warnings[0].startswith(
            "Without tracked_item_names, 2 column-0 'Key:' line(s) on 2 turn(s) were kept "
            "inside tracked-item values"
        )
        assert "Pass tracked_item_names" in summary.warnings[0]

    def test_no_column0_warning_with_names(self, tmp_path):
        src = _export(tmp_path, ("Gold:\n5\n\nHP:\n10", None))
        summary = extract_story_data(
            [src], str(tmp_path / "out"), tracked_item_names=["Gold", "HP"]
        )
        assert summary.warnings == []

    def test_hidden_keyset_change_warns(self, tmp_path):
        src = _export(tmp_path, ("A:\n1", "S:\nx"), ("A:\n1", "S:\nx\n\nT:\ny"))
        summary = extract_story_data([src], str(tmp_path / "out"))
        assert len(summary.warnings) == 1
        assert summary.warnings[0].startswith(
            "Hidden Tracked Items: keys changed between turns 1 and 2 (added: ['T']"
        )

    def test_keyset_warning_sorts_turns(self):
        turns = [_turn(2, {"A": "1", "B": "2"}), _turn(1, {"A": "1"})]
        warnings = _tracked_item_warnings(turns, None, [])
        assert len(warnings) == 1
        assert "between turns 1 and 2 (added: ['B']; removed: [])" in warnings[0]

    def test_unassigned_text_warns(self, tmp_path):
        src = _export(tmp_path, ("stray note\n\nA:\n1", None))
        summary = extract_story_data([src], str(tmp_path / "out"), tracked_item_names=["A"])
        assert summary.warnings == [
            "1 non-blank line(s) before the first tracked-item name could not be assigned to "
            "any item and were dropped (turns 1)."
        ]

    def test_header_starting_items_use_names(self, tmp_path):
        src = tmp_path / "export.txt"
        src.write_text(
            "== T ==\n\n-- Character --\n\nName\n----\nX\n\n"
            "Starting Tracked Items\n----------------------\nNotes:\nline\n\nInner:\nmore\n\n"
            "-- Turn 1 --\n\nOutcome\n-------\nA.\n\n"
            "Tracked Items\n-------------\nNotes:\nline\n"
        )
        summary = extract_story_data(
            [str(src)], str(tmp_path / "out"), tracked_item_names=["Notes"]
        )
        with open(tmp_path / "out" / "metadata.json") as fh:
            starting = json.load(fh)["character"]["startingTrackedItems"]
        assert starting == {"Notes": "line\n\nInner:\nmore"}
        # The header's split is not silent: an unlisted name line is reported there too.
        assert summary.warnings == [
            "Starting Tracked Items: line 'Inner:' is not in tracked_item_names, so it was kept "
            "inside the value of the listed item above it (the header). Add the name if it is a "
            "real item."
        ]
