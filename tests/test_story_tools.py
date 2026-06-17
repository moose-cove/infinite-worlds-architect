"""Tests for the story-extraction MCP tool wrappers (iw_architect.tools.story_tools).

These exercise the MCP boundary: absolute-path enforcement, the camelCase JSON
wire shape, the bare ``{"error": ...}`` failure convention (no ``success`` key),
and server registration.
"""

import json
import os

import pytest

from iw_architect.tools.story_tools import (
    extract_story_data,
    get_character_list,
    query_story_data,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name: str) -> str:
    """Absolute path to a committed story-export fixture."""
    return os.path.join(FIXTURES, name)


def _write_world(tmp_path, world: dict) -> str:
    """Write a world dict to an absolute tmp path and return it."""
    path = tmp_path / "world.json"
    path.write_text(json.dumps(world))
    return str(path)


# ---------------------------------------------------------------------------
# extract_story_data
# ---------------------------------------------------------------------------


class TestExtractStoryData:
    def test_success_returns_camelcase_summary(self, tmp_path):
        out = json.loads(
            extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        )
        # camelCase wire keys, snake_case absent.
        assert out["totalTurns"] == 5
        assert "total_turns" not in out
        assert out["turnRange"] == {"min": 1, "max": 5}
        assert "manifest.json" in out["filesWritten"]
        assert "error" not in out

    def test_no_success_key(self, tmp_path):
        out = json.loads(
            extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        )
        assert "success" not in out

    def test_writes_files_to_extraction_dir(self, tmp_path):
        extract_story_data([fixture("story_export_single_5turn.txt")], str(tmp_path))
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "metadata.json").exists()
        assert (tmp_path / "turn_index.json").exists()

    def test_character_list_writes_character_index(self, tmp_path):
        out = json.loads(
            extract_story_data(
                [fixture("story_export_single_5turn.txt")],
                str(tmp_path),
                character_list=[{"name": "Petra Voss", "aliases": ["Petra"]}],
            )
        )
        assert "character_index.json" in out["filesWritten"]
        assert (tmp_path / "character_index.json").exists()

    def test_relative_input_path_errors(self, tmp_path):
        out = json.loads(extract_story_data(["story_export_single_5turn.txt"], str(tmp_path)))
        assert "error" in out
        assert "relative path" in out["error"]

    def test_relative_extraction_dir_errors(self):
        out = json.loads(extract_story_data([fixture("story_export_single_5turn.txt")], "out_dir"))
        assert "error" in out

    def test_empty_input_paths_errors(self, tmp_path):
        out = json.loads(extract_story_data([], str(tmp_path)))
        assert "error" in out
        assert "at least one" in out["error"]

    def test_no_turn1_errors(self, tmp_path):
        out = json.loads(extract_story_data([fixture("story_export_no_turn1.txt")], str(tmp_path)))
        assert "error" in out

    def test_missing_input_file_errors(self, tmp_path):
        out = json.loads(extract_story_data([str(tmp_path / "nope.txt")], str(tmp_path)))
        assert "error" in out


# ---------------------------------------------------------------------------
# query_story_data
# ---------------------------------------------------------------------------


@pytest.fixture()
def extraction_dir(tmp_path):
    """An extraction directory produced from the 5-turn fixture (with characters)."""
    extract_story_data(
        [fixture("story_export_single_5turn.txt")],
        str(tmp_path),
        character_list=[{"name": "Petra Voss", "aliases": ["Petra"]}],
    )
    return str(tmp_path)


class TestQueryStoryData:
    def test_manifest_camelcase(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "manifest"))
        assert out["totalTurns"] == 5
        assert "total_turns" not in out
        assert "sources" in out

    def test_metadata(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "metadata"))
        assert out["title"] == "The Iron Gate"
        assert out["objective"] is None

    def test_turn_index_filter_last(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "turn_index", turns=["last"]))
        assert len(out["turns"]) == 1
        assert out["turns"][0]["number"] == 5

    def test_turn_detail_raw_slice(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "turn_detail", turns=["2"]))
        assert out["turnDetail"][0]["turn"] == 2
        assert len(out["turnDetail"][0]["raw"]) > 0

    def test_character_index(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "character_index"))
        assert "Petra Voss" in out["characters"]

    def test_relative_dir_errors(self):
        out = json.loads(query_story_data("rel_dir", "manifest"))
        assert "error" in out
        assert "relative path" in out["error"]

    def test_unknown_category_errors(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "bogus"))
        assert "error" in out
        assert "Unknown category" in out["error"]

    def test_turn_detail_requires_turns(self, extraction_dir):
        out = json.loads(query_story_data(extraction_dir, "turn_detail"))
        assert "error" in out

    def test_missing_manifest_errors(self, tmp_path):
        out = json.loads(query_story_data(str(tmp_path / "empty"), "manifest"))
        assert "error" in out


# ---------------------------------------------------------------------------
# get_character_list
# ---------------------------------------------------------------------------


class TestGetCharacterList:
    def test_includes_player_characters_and_npcs(self, tmp_path):
        world = {
            "possibleCharacters": [{"characterId": "ab12CD34", "name": "Petra Voss"}],
            "NPCs": [{"id": "warden01x", "name": "The Warden"}],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        names = [c["name"] for c in out["character_list"]]
        assert "Petra Voss" in names  # protagonist (possibleCharacters) not omitted
        assert "The Warden" in names
        assert out["source_count"] == 2

    def test_player_character_aliases_default_empty(self, tmp_path):
        # possibleCharacters have no alias field in the schema → aliases stay [].
        world = {"possibleCharacters": [{"name": "Petra Voss"}], "NPCs": []}
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert out["character_list"][0]["aliases"] == []

    def test_npc_aliases_seeded_from_names(self, tmp_path):
        # IW NPCs carry a `names` field (schema: "alternative names the NPC may go
        # by"); it must seed the character-index alias list.
        world = {
            "possibleCharacters": [],
            "NPCs": [{"name": "Finnegan Mosswood", "names": ["Finn", "Mosswood"]}],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        entry = out["character_list"][0]
        assert entry["name"] == "Finnegan Mosswood"
        assert entry["aliases"] == ["Finn", "Mosswood"]

    def test_npc_aliases_exclude_canonical_name_and_dedupe(self, tmp_path):
        world = {
            "possibleCharacters": [],
            "NPCs": [{"name": "Finn", "names": ["Finn", "Finnegan", "Finnegan", ""]}],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        # The canonical name, duplicates, and blank entries are dropped.
        assert out["character_list"][0]["aliases"] == ["Finnegan"]

    def test_player_characters_before_npcs(self, tmp_path):
        world = {
            "possibleCharacters": [{"name": "Petra Voss"}],
            "NPCs": [{"name": "The Warden"}],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert [c["name"] for c in out["character_list"]] == ["Petra Voss", "The Warden"]

    def test_nameless_entries_skipped(self, tmp_path):
        world = {
            "possibleCharacters": [{"characterId": "noName01"}, {"name": "Petra Voss"}],
            "NPCs": [],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert out["source_count"] == 1
        assert out["character_list"][0]["name"] == "Petra Voss"

    def test_duplicate_names_deduped(self, tmp_path):
        world = {
            "possibleCharacters": [{"name": "Petra Voss"}],
            "NPCs": [{"name": "Petra Voss"}],
        }
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert out["source_count"] == 1

    def test_empty_world(self, tmp_path):
        out = json.loads(get_character_list(_write_world(tmp_path, {})))
        assert out["character_list"] == []
        assert out["source_count"] == 0

    def test_non_dict_entries_skipped(self, tmp_path):
        # Defensive: a malformed world with non-dict array members must not crash.
        world = {"possibleCharacters": [None, "oops", {"name": "Petra Voss"}], "NPCs": []}
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert out["source_count"] == 1
        assert out["character_list"][0]["name"] == "Petra Voss"

    def test_non_list_character_fields_tolerated(self, tmp_path):
        # Defensive: a malformed world where the character fields aren't lists.
        world = {"possibleCharacters": "bogus", "NPCs": {"name": "X"}}
        out = json.loads(get_character_list(_write_world(tmp_path, world)))
        assert out["character_list"] == []
        assert out["source_count"] == 0

    def test_relative_path_errors(self):
        out = json.loads(get_character_list("world.json"))
        assert "error" in out
        assert "relative path" in out["error"]

    def test_missing_file_errors(self, tmp_path):
        out = json.loads(get_character_list(str(tmp_path / "nope.json")))
        assert "error" in out

    def test_invalid_json_errors(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        out = json.loads(get_character_list(str(bad)))
        assert "error" in out


# ---------------------------------------------------------------------------
# server registration
# ---------------------------------------------------------------------------


class TestServerRegistration:
    def test_server_registers_story_tools(self):
        # Registration smoke: the server module imports cleanly with the new tools.
        import iw_architect.server as server

        assert callable(server.extract_story_data)
        assert callable(server.query_story_data)
        assert callable(server.get_character_list)
