"""Tests for iw_architect.story.query."""

import json
import os

import pytest

from iw_architect.story.extract import extract_story_data
from iw_architect.story.query import query_story_data

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name: str) -> str:
    return os.path.join(FIXTURES, name)


@pytest.fixture()
def extracted(tmp_path):
    """Run extraction on single_5turn.txt and return the extraction_dir."""
    extract_story_data(
        [fixture("story_export_single_5turn.txt")],
        str(tmp_path),
        character_list=[{"name": "Petra Voss", "aliases": ["Petra"]}],
    )
    return str(tmp_path)


@pytest.fixture()
def extracted_no_hidden(tmp_path):
    extract_story_data([fixture("story_export_no_hidden.txt")], str(tmp_path))
    return str(tmp_path)


class TestQueryManifest:
    def test_returns_manifest(self, extracted):
        result = query_story_data(extracted, "manifest")
        assert "total_turns" in result
        assert result["total_turns"] == 5

    def test_files_written_listed(self, extracted):
        result = query_story_data(extracted, "manifest")
        assert "manifest.json" in result["filesWritten"]


class TestQueryMetadata:
    def test_returns_metadata(self, extracted):
        result = query_story_data(extracted, "metadata")
        assert result["title"] == "The Iron Gate"

    def test_objective_is_none(self, extracted):
        result = query_story_data(extracted, "metadata")
        assert result["objective"] is None


class TestQueryTurnIndex:
    def test_returns_all_turns(self, extracted):
        result = query_story_data(extracted, "turn_index")
        assert len(result["turns"]) == 5

    def test_filter_by_turn_number(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["2"])
        assert len(result["turns"]) == 1
        assert result["turns"][0]["number"] == 2

    def test_filter_by_last(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["last"])
        assert result["turns"][0]["number"] == 5

    def test_filter_multiple_turns(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["1", "3"])
        numbers = [t["number"] for t in result["turns"]]
        assert set(numbers) == {1, 3}


class TestQueryTrackedState:
    def test_returns_snapshots(self, extracted):
        result = query_story_data(extracted, "tracked_state")
        assert "snapshots" in result
        assert len(result["snapshots"]) >= 1

    def test_filter_by_turn(self, extracted):
        result = query_story_data(extracted, "tracked_state", turns=["1"])
        # Only snapshots whose range includes turn 1.
        for snap in result["snapshots"]:
            assert snap["fromTurn"] <= 1 <= snap["toTurn"]

    def test_filter_by_last(self, extracted):
        result = query_story_data(extracted, "tracked_state", turns=["last"])
        # All snapshots including turn 5.
        for snap in result["snapshots"]:
            assert snap["toTurn"] >= 5 or snap["fromTurn"] <= 5

    def test_missing_file_raises(self, extracted_no_hidden, tmp_path):
        # Test a dir that has no tracked_state.json.
        empty_dir = str(tmp_path / "empty")
        os.makedirs(empty_dir)
        # Write a minimal manifest so query can read total_turns.
        manifest = {
            "total_turns": 2,
            "files_written": ["manifest.json"],
            "warnings": [],
            "input_paths": [],
            "extraction_dir": empty_dir,
        }
        with open(os.path.join(empty_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)
        with pytest.raises(FileNotFoundError):
            query_story_data(empty_dir, "tracked_state")


class TestQueryTurnDetail:
    def test_returns_raw_lines(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["1"])
        assert "turn_detail" in result
        assert len(result["turn_detail"]) == 1
        detail = result["turn_detail"][0]
        assert detail["turn"] == 1
        assert isinstance(detail["raw"], str)
        assert len(detail["raw"]) > 0

    def test_turn_detail_contains_source_path(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["2"])
        detail = result["turn_detail"][0]
        assert os.path.isabs(detail["source"])

    def test_turn_detail_last(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["last"])
        detail = result["turn_detail"][0]
        assert detail["turn"] == 5

    def test_turn_detail_requires_turns_arg(self, extracted):
        with pytest.raises(ValueError, match="turn_detail requires"):
            query_story_data(extracted, "turn_detail")

    def test_turn_detail_invalid_turn_raises(self, extracted):
        with pytest.raises(ValueError, match="not found in turn_index"):
            query_story_data(extracted, "turn_detail", turns=["99"])


class TestQueryCharacterIndex:
    def test_returns_character_index(self, extracted):
        result = query_story_data(extracted, "character_index")
        assert "characters" in result
        assert "Petra Voss" in result["characters"]

    def test_missing_character_index_raises(self, tmp_path):
        # Extract without character_list → no character_index.json.
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        with pytest.raises(FileNotFoundError):
            query_story_data(str(tmp_path), "character_index")


class TestQueryMissingManifest:
    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="manifest.json"):
            query_story_data(str(tmp_path), "manifest")


class TestQueryInvalidCategory:
    def test_invalid_category_raises(self, extracted):
        with pytest.raises(ValueError, match="Unknown category"):
            query_story_data(extracted, "bogus")
