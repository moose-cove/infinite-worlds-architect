"""Tests for iw_architect.story.extract."""

import json
import os

import pytest

from iw_architect.story.extract import extract_story_data

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name: str) -> str:
    return os.path.join(FIXTURES, name)


class TestExtractBasic:
    def test_returns_manifest_dict(self, tmp_path):
        manifest = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert isinstance(manifest, dict)
        assert "total_turns" in manifest
        assert "files_written" in manifest

    def test_total_turns_is_five(self, tmp_path):
        manifest = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert manifest["total_turns"] == 5

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
        manifest = extract_story_data(
            [fixture("story_export_single_5turn.txt")],
            str(tmp_path),
            character_list=[{"name": "Petra Voss", "aliases": []}],
        )
        assert (tmp_path / "character_index.json").exists()
        assert len(manifest["files_written"]) == 5

    def test_four_files_no_character_list(self, tmp_path):
        manifest = extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert len(manifest["files_written"]) == 4

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
        manifest = extract_story_data([str(src)], str(tmp_path / "out"))
        assert len(manifest["files_written"]) == 3
        assert not (tmp_path / "out" / "tracked_state.json").exists()


class TestExtractIdempotent:
    def test_rerun_overwrites(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        # Modify manifest to check it's overwritten.
        m_path = tmp_path / "manifest.json"
        with open(m_path) as f:
            original = json.load(f)
        # Second run.
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(m_path) as f:
            second = json.load(f)
        assert original["total_turns"] == second["total_turns"]


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

    def test_metadata_character_name(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
        assert meta["character"]["name"] == "Petra Voss"

    def test_metadata_starting_tracked_items(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with open(tmp_path / "metadata.json") as f:
            meta = json.load(f)
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

    def test_no_hidden_file_tracked_state_written(self, tmp_path):
        extract_story_data([fixture("story_export_no_hidden.txt")], str(tmp_path))
        assert (tmp_path / "tracked_state.json").exists()


class TestExtractCreatesDir:
    def test_creates_extraction_dir_if_not_exists(self, tmp_path):
        out = tmp_path / "new_dir"
        assert not out.exists()
        extract_story_data([fixture("story_export_single_5turn.txt")], str(out))
        assert out.exists()
