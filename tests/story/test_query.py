"""Tests for iw_architect.story.query."""

import json
import os

import pytest

from iw_architect.story.extract import extract_story_data
from iw_architect.story.models import (
    CharacterIndex,
    Manifest,
    Metadata,
    TrackedState,
    TurnIndex,
)
from iw_architect.story.query import query_story_data

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


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
    def test_returns_manifest_model(self, extracted):
        result = query_story_data(extracted, "manifest")
        assert isinstance(result, Manifest)

    def test_total_turns_via_snake_attr(self, extracted):
        result = query_story_data(extracted, "manifest")
        # Access via snake_case attribute (populated from camelCase JSON key totalTurns).
        assert result.total_turns == 5

    def test_files_written_listed(self, extracted):
        result = query_story_data(extracted, "manifest")
        assert "manifest.json" in result.files_written

    def test_manifest_has_sources(self, extracted):
        result = query_story_data(extracted, "manifest")
        assert len(result.sources) >= 1


class TestQueryMetadata:
    def test_returns_metadata_model(self, extracted):
        result = query_story_data(extracted, "metadata")
        assert isinstance(result, Metadata)

    def test_returns_metadata(self, extracted):
        result = query_story_data(extracted, "metadata")
        assert result.title == "The Iron Gate"

    def test_objective_is_none(self, extracted):
        result = query_story_data(extracted, "metadata")
        assert result.objective is None

    def test_story_background_snake_attr(self, extracted):
        result = query_story_data(extracted, "metadata")
        # story_background populated from camelCase storyBackground on disk.
        assert result.story_background is not None


class TestQueryTurnIndex:
    def test_returns_turn_index_model(self, extracted):
        result = query_story_data(extracted, "turn_index")
        assert isinstance(result, TurnIndex)

    def test_returns_all_turns(self, extracted):
        result = query_story_data(extracted, "turn_index")
        assert len(result.turns) == 5

    def test_filter_by_turn_number(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["2"])
        assert len(result.turns) == 1
        assert result.turns[0].number == 2

    def test_filter_by_last(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["last"])
        assert result.turns[0].number == 5

    def test_filter_multiple_turns(self, extracted):
        result = query_story_data(extracted, "turn_index", turns=["1", "3"])
        numbers = [t.number for t in result.turns]
        assert set(numbers) == {1, 3}

    def test_turn_snake_attrs(self, extracted):
        result = query_story_data(extracted, "turn_index")
        turn1 = next(t for t in result.turns if t.number == 1)
        # snake_case attribute access
        assert turn1.action is None
        assert turn1.line_range[0] >= 1
        assert turn1.secret_info is None or isinstance(turn1.secret_info, str)


class TestQueryTrackedState:
    def test_returns_tracked_state_model(self, extracted):
        result = query_story_data(extracted, "tracked_state")
        assert isinstance(result, TrackedState)

    def test_returns_snapshots(self, extracted):
        result = query_story_data(extracted, "tracked_state")
        assert len(result.snapshots) >= 1

    def test_filter_by_turn(self, extracted):
        result = query_story_data(extracted, "tracked_state", turns=["1"])
        # Only snapshots whose range includes turn 1.
        for snap in result.snapshots:
            assert snap.from_turn <= 1 <= snap.to_turn

    def test_filter_by_last(self, extracted):
        result = query_story_data(extracted, "tracked_state", turns=["last"])
        # All snapshots including turn 5.
        for snap in result.snapshots:
            assert snap.to_turn >= 5 or snap.from_turn <= 5

    def test_missing_file_raises(self, extracted_no_hidden, tmp_path):
        # Test a dir that has no tracked_state.json.
        empty_dir = str(tmp_path / "empty")
        os.makedirs(empty_dir)
        # Write a minimal manifest so query can read totalTurns.
        manifest = {
            "totalTurns": 2,
            "turnRange": {"min": 1, "max": 2},
            "inputFilesProcessed": 1,
            "hasTrackedItems": False,
            "hasHiddenTrackedItems": False,
            "filesWritten": ["manifest.json"],
            "warnings": [],
            "sources": [],
        }
        with open(os.path.join(empty_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)
        with pytest.raises(FileNotFoundError):
            query_story_data(empty_dir, "tracked_state")


class TestQueryTurnDetail:
    def test_returns_turn_detail_list(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["1"])
        assert hasattr(result, "turn_detail")
        assert len(result.turn_detail) == 1

    def test_turn_detail_model_attrs(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["1"])
        detail = result.turn_detail[0]
        assert detail.turn == 1
        assert isinstance(detail.raw, str)
        assert len(detail.raw) > 0

    def test_turn_detail_contains_source_path(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["2"])
        detail = result.turn_detail[0]
        assert os.path.isabs(detail.source)

    def test_turn_detail_last(self, extracted):
        result = query_story_data(extracted, "turn_detail", turns=["last"])
        detail = result.turn_detail[0]
        assert detail.turn == 5

    def test_turn_detail_requires_turns_arg(self, extracted):
        with pytest.raises(ValueError, match="turn_detail requires"):
            query_story_data(extracted, "turn_detail")

    def test_turn_detail_invalid_turn_raises(self, extracted):
        with pytest.raises(ValueError, match="not found in turn_index"):
            query_story_data(extracted, "turn_detail", turns=["99"])


class TestQueryCharacterIndex:
    def test_returns_character_index_model(self, extracted):
        result = query_story_data(extracted, "character_index")
        assert isinstance(result, CharacterIndex)

    def test_returns_character_index(self, extracted):
        result = query_story_data(extracted, "character_index")
        assert "Petra Voss" in result.characters

    def test_character_index_snake_attrs(self, extracted):
        result = query_story_data(extracted, "character_index")
        assert result.indexed_character_count >= 1
        assert result.total_mentions >= 0

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
