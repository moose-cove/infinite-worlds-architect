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


# ---------------------------------------------------------------------------
# items / changes_only (story_export_yaml_tracked.txt)
# ---------------------------------------------------------------------------

YAML_NAMES = ["Level", "Exp ", "Spells", "Abilities", "Dead", "Deeds", "Notes", "Secret Plans"]


@pytest.fixture()
def extracted_yaml(tmp_path):
    extract_story_data(
        [fixture("story_export_yaml_tracked.txt")], str(tmp_path), tracked_item_names=YAML_NAMES
    )
    return str(tmp_path)


def _ranges(state: TrackedState) -> list[tuple[int, int]]:
    return [(s.from_turn, s.to_turn) for s in state.snapshots]


class TestQueryItems:
    def test_items_projects_both_dicts(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "tracked_state", items=["Level", "Secret Plans"])
        assert len(result.snapshots) == 3
        for snap in result.snapshots:
            assert list(snap.tracked_items) == ["Level"]
            assert list(snap.hidden_tracked_items) == ["Secret Plans"]

    def test_items_on_turn_index(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "turn_index", items=["Dead"], turns=[2])
        assert [t.number for t in result.turns] == [2]
        assert list(result.turns[0].tracked_items) == ["Dead"]
        assert result.turns[0].hidden_tracked_items == {}
        assert result.turns[0].outcome  # non-tracked fields untouched

    def test_loose_match_resolves_trailing_space(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "tracked_state", items=["exp"])
        assert [s.tracked_items for s in result.snapshots] == [
            {"Exp ": "0 / 10"},
            {"Exp ": "6 / 10"},
            {"Exp ": "0 / 20"},
        ]

    def test_unknown_item_lists_available(self, extracted_yaml):
        with pytest.raises(ValueError, match="Unknown tracked item name") as exc:
            query_story_data(extracted_yaml, "tracked_state", items=["Gold"])
        assert "'Exp '" in str(exc.value)
        assert "'Secret Plans'" in str(exc.value)

    def test_ambiguous_loose_match_raises(self, tmp_path):
        src = tmp_path / "export.txt"
        src.write_text(
            "== T ==\n\n-- Turn 1 --\n\nOutcome\n-------\nA.\n\n"
            "Tracked Items\n-------------\nGold:\n1\n\nGOLD:\n2\n"
        )
        extract_story_data([str(src)], str(tmp_path / "out"))
        with pytest.raises(ValueError, match="ambiguous"):
            query_story_data(str(tmp_path / "out"), "tracked_state", items=["gold"])

    def test_items_rejected_for_other_categories(self, extracted_yaml):
        with pytest.raises(ValueError, match="items is only supported"):
            query_story_data(extracted_yaml, "manifest", items=["Level"])


class TestQueryChangesOnly:
    def test_merges_unchanged_runs(self, extracted_yaml):
        level = query_story_data(
            extracted_yaml, "tracked_state", items=["Level"], changes_only=True
        )
        assert _ranges(level) == [(1, 2), (3, 3)]
        dead = query_story_data(extracted_yaml, "tracked_state", items=["Dead"], changes_only=True)
        assert _ranges(dead) == [(1, 1), (2, 3)]
        deeds = query_story_data(
            extracted_yaml, "tracked_state", items=["Deeds"], changes_only=True
        )
        assert _ranges(deeds) == [(1, 3)]

    def test_multiple_items_change_when_either_changes(self, extracted_yaml):
        result = query_story_data(
            extracted_yaml, "tracked_state", items=["Level", "Dead"], changes_only=True
        )
        assert _ranges(result) == [(1, 1), (2, 2), (3, 3)]

    def test_with_turns_merges_only_true_neighbours(self, extracted_yaml):
        gap = query_story_data(
            extracted_yaml, "tracked_state", turns=[1, 3], items=["Deeds"], changes_only=True
        )
        assert _ranges(gap) == [(1, 1), (3, 3)]
        adjacent = query_story_data(
            extracted_yaml, "tracked_state", turns=[2, "last"], items=["Dead"], changes_only=True
        )
        assert _ranges(adjacent) == [(2, 3)]

    def test_requires_items(self, extracted_yaml):
        with pytest.raises(ValueError, match="changes_only requires items"):
            query_story_data(extracted_yaml, "tracked_state", changes_only=True)

    def test_rejected_for_turn_index(self, extracted_yaml):
        with pytest.raises(ValueError, match="changes_only is only supported"):
            query_story_data(extracted_yaml, "turn_index", items=["Level"], changes_only=True)


class TestQueryItemsEdges:
    def test_changes_only_compares_hidden_items(self, extracted_yaml):
        result = query_story_data(
            extracted_yaml, "tracked_state", items=["Secret Plans"], changes_only=True
        )
        assert _ranges(result) == [(1, 2), (3, 3)]
        assert all(s.tracked_items == {} for s in result.snapshots)

    def test_tracked_state_projection_empties_hidden(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "tracked_state", items=["Level"])
        assert all(s.hidden_tracked_items == {} for s in result.snapshots)

    def test_padded_upper_case_resolves(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "tracked_state", items=[" EXP "])
        assert list(result.snapshots[0].tracked_items) == ["Exp "]

    def test_order_follows_request(self, extracted_yaml):
        result = query_story_data(extracted_yaml, "tracked_state", items=["Dead", "Level"])
        assert list(result.snapshots[0].tracked_items) == ["Dead", "Level"]
        turns = query_story_data(extracted_yaml, "turn_index", items=["Dead", "Level"])
        assert list(turns.turns[0].tracked_items) == ["Dead", "Level"]

    def test_duplicate_requested_names_collapse(self, extracted_yaml):
        result = query_story_data(
            extracted_yaml, "tracked_state", items=["Level", "level", "Level"]
        )
        assert list(result.snapshots[0].tracked_items) == ["Level"]

    def test_absent_section_stays_none(self, extracted_no_hidden):
        result = query_story_data(extracted_no_hidden, "tracked_state", items=["Miles Walked"])
        assert all(s.hidden_tracked_items is None for s in result.snapshots)
        assert all(list(s.tracked_items) == ["Miles Walked"] for s in result.snapshots)

    @pytest.mark.parametrize("category", ["tracked_state", "turn_index"])
    def test_empty_items_rejected(self, extracted_yaml, category):
        with pytest.raises(ValueError, match="items must name at least one tracked item"):
            query_story_data(extracted_yaml, category, items=[])
