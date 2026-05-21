"""Validator negative tests.

For each error class in the design brief §4.6, a fixture that triggers the error
must cause validate_world to report it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _write_world(world: dict) -> str:
    """Write a world dict to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False)
    json.dump(world, tmp)
    tmp.flush()
    return tmp.name


def _validate(world: dict) -> dict:
    from iw_architect.validator import validate_world

    path = _write_world(world)
    try:
        return json.loads(validate_world(path))
    finally:
        Path(path).unlink(missing_ok=True)


def _base_world(**overrides) -> dict:
    """Minimal valid world scaffold for test mutations."""
    import tempfile

    from iw_architect.tools.helpers import scaffold_world

    tmp = tempfile.mktemp(suffix=".json")
    scaffold_world(tmp, title="Test World")
    world = json.loads(Path(tmp).read_text())
    Path(tmp).unlink(missing_ok=True)
    world.update(overrides)
    return world


# ── Type errors ───────────────────────────────────────────────────────────────


def test_wrong_type_mature():
    world = _base_world(mature="yes")  # should be boolean
    result = _validate(world)
    assert not result["valid"]
    assert any("mature" in e for e in result["errors"])


def test_wrong_type_schema_version():
    world = _base_world(schemaVersion="2.1")  # should be number
    result = _validate(world)
    assert not result["valid"]
    assert any("schemaVersion" in e for e in result["errors"])


def test_wrong_type_skills():
    world = _base_world(skills="Baking")  # should be array
    result = _validate(world)
    assert not result["valid"]
    assert any("skills" in e for e in result["errors"])


# ── Missing required fields ───────────────────────────────────────────────────


def test_missing_schema_version():
    world = _base_world()
    del world["schemaVersion"]
    result = _validate(world)
    assert not result["valid"]
    assert any("schemaVersion" in e for e in result["errors"])


def test_missing_title():
    world = _base_world()
    del world["title"]
    result = _validate(world)
    assert not result["valid"]
    assert any("title" in e for e in result["errors"])


# ── Invalid enum values ───────────────────────────────────────────────────────


def test_invalid_tracked_item_data_type():
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "abc123def",
            "name": "Health",
            "positionInList": 0,
            "dataType": "integer",  # invalid — must be text/number/xml
            "visibility": "everyone",
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("dataType" in e or "integer" in e for e in result["errors"])


def test_invalid_tracked_item_visibility():
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "abc123def",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "public",  # invalid
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("visibility" in e or "public" in e for e in result["errors"])


# ── Broken cross-references ───────────────────────────────────────────────────


def test_trigger_on_character_unknown_id():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "condition",
                    "type": "triggerOnCharacter",
                    "data": ["UNKNOWN_CHAR_ID"],
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("UNKNOWN_CHAR_ID" in e for e in result["errors"])


def test_effect_modify_instruction_block_unknown_id():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectModifyInstructionBlock",
                    "data": {"id": "NONEXISTENT", "content": "new content"},
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("NONEXISTENT" in e for e in result["errors"])


def test_trigger_prereqs_unknown_id():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "condition",
                    "type": "triggerPrereqs",
                    "data": ["DOES_NOT_EXIST"],
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("DOES_NOT_EXIST" in e for e in result["errors"])


def test_trigger_blockers_unknown_id():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "condition",
                    "type": "triggerBlockers",
                    "data": ["DOES_NOT_EXIST"],
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("DOES_NOT_EXIST" in e for e in result["errors"])


# ── Duplicate IDs ─────────────────────────────────────────────────────────────


def test_duplicate_tracked_item_ids():
    world = _base_world()
    item = {
        "id": "DUPID1234",
        "name": "Health",
        "positionInList": 0,
        "dataType": "number",
        "visibility": "everyone",
        "autoUpdate": False,
    }
    world["trackedItems"] = [item, {**item, "name": "Health2", "positionInList": 1}]
    result = _validate(world)
    assert not result["valid"]
    assert any("DUPID1234" in e for e in result["errors"])


def test_duplicate_npc_ids():
    world = _base_world()
    npc = {"id": "NPC00001A", "name": "Bob", "positionInList": 0}
    world["NPCs"] = [npc, {**npc, "name": "Alice", "positionInList": 1}]
    result = _validate(world)
    assert not result["valid"]
    assert any("NPC00001A" in e for e in result["errors"])


# ── positionInList ─────────────────────────────────────────────────────────────


def test_non_unique_position_in_list():
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
        },
        {
            "id": "ITEM00002",
            "name": "Mana",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
        },
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("positionInList" in e for e in result["errors"])


# ── Cross-field invariants ────────────────────────────────────────────────────


def test_nsfw_requires_mature():
    world = _base_world(nsfw=True, mature=False)
    result = _validate(world)
    assert not result["valid"]
    assert any("nsfw" in e and "mature" in e for e in result["errors"])


def test_nsfw_with_mature_is_valid():
    world = _base_world(nsfw=True, mature=True)
    result = _validate(world)
    assert result["valid"]


def test_editing_requires_sharing():
    world = _base_world()
    world["permissionsOnceShared"] = {"sharing": False, "editing": True}
    result = _validate(world)
    assert not result["valid"]
    assert any("editing" in e and "sharing" in e for e in result["errors"])


# ── Logic conditions ──────────────────────────────────────────────────────────


def test_logic_condition_requires_advanced_logic():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "advancedLogic": False,
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "logic",
                    "operator": "or",
                    "data": [],
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("logic" in e.lower() and "advancedLogic" in e for e in result["errors"])


def test_logic_condition_with_advanced_logic_is_valid():
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "advancedLogic": True,
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "logic",
                    "operator": "or",
                    "data": [],
                }
            ],
        }
    ]
    result = _validate(world)
    assert result["valid"]


# ── Schema version warnings ────────────────────────────────────────────────────


def test_future_schema_version_warns():
    world = _base_world(schemaVersion=99.0)
    result = _validate(world)
    assert result["valid"]  # must warn, not error
    assert any("99.0" in w or "newer" in w for w in result["warnings"])


# ── Unknown top-level keys produce warnings, not errors ───────────────────────


def test_unknown_top_level_key_is_warning():
    world = _base_world()
    world["someUnknownPlatformField"] = "value"
    result = _validate(world)
    assert result["valid"]
    assert any("someUnknownPlatformField" in w for w in result["warnings"])


# ── Tool function tests ────────────────────────────────────────────────────────


def test_read_world_field_simple():

    from iw_architect.tools.inspection import read_world_field

    world = _base_world(background="The adventure begins")
    path = _write_world(world)
    try:
        result = json.loads(read_world_field(path, "background"))
        assert result["value"] == "The adventure begins"
    finally:
        Path(path).unlink(missing_ok=True)


def test_read_world_field_dotted():

    from iw_architect.tools.inspection import read_world_field

    world = _base_world()
    world["imagePromptDetails"] = {"illustrGenre": "fantasy"}
    path = _write_world(world)
    try:
        result = json.loads(read_world_field(path, "imagePromptDetails.illustrGenre"))
        assert result["value"] == "fantasy"
    finally:
        Path(path).unlink(missing_ok=True)


def test_read_world_field_index_bracket():
    from iw_architect.tools.inspection import read_world_field

    world = _base_world()
    world["skills"] = ["Baking", "Creativity"]
    path = _write_world(world)
    try:
        result = json.loads(read_world_field(path, "skills[0]"))
        assert result["value"] == "Baking"
    finally:
        Path(path).unlink(missing_ok=True)


def test_read_world_field_name_bracket():
    from iw_architect.tools.inspection import read_world_field

    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
            "initialValue": "100",
        }
    ]
    path = _write_world(world)
    try:
        result = json.loads(read_world_field(path, "trackedItems[name=Health].initialValue"))
        assert result["value"] == "100"
    finally:
        Path(path).unlink(missing_ok=True)


def test_mint_ids_character():
    from iw_architect.tools.helpers import mint_ids

    result = json.loads(mint_ids("character", 3))
    assert len(result["ids"]) == 3
    for id_ in result["ids"]:
        assert len(id_) == 8


def test_mint_ids_npc():
    from iw_architect.tools.helpers import mint_ids

    result = json.loads(mint_ids("npc", 1))
    assert len(result["ids"]) == 1
    assert len(result["ids"][0]) == 9


def test_mint_ids_trigger_step_is_uuid():
    import uuid

    from iw_architect.tools.helpers import mint_ids

    result = json.loads(mint_ids("triggerStep", 1))
    assert len(result["ids"]) == 1
    # Should be parseable as UUID
    uuid.UUID(result["ids"][0])


def test_mint_ids_invalid_kind():
    from iw_architect.tools.helpers import mint_ids

    result = json.loads(mint_ids("unknown_kind", 1))
    assert "error" in result


def test_confirm_path_existing(tmp_path):
    from iw_architect.tools.helpers import confirm_path

    result = json.loads(confirm_path(str(tmp_path)))
    assert result["exists"]
    assert result["status"] == "ok"


def test_confirm_path_new_file(tmp_path):
    from iw_architect.tools.helpers import confirm_path

    new_file = tmp_path / "new_world.json"
    result = json.loads(confirm_path(str(new_file)))
    assert not result["exists"]
    assert result["parent_exists"]
    assert result["status"] == "ok"


def test_get_schema_summary():
    from iw_architect.tools.inspection import get_schema_summary

    result = json.loads(get_schema_summary())
    assert "entityTypes" in result
    assert "effectTypes" in result
    assert "conditionTypes" in result


def test_audit_world_fixture():
    """audit_world must return findings (not error) on the canonical fixture."""
    from iw_architect.tools.analysis import audit_world

    fixture = Path(__file__).parent.parent / "example-world-schema-v2.1.json"
    result = json.loads(audit_world(str(fixture)))
    assert "findings" in result
    assert isinstance(result["findings"], list)


def test_compare_worlds_no_changes(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import scaffold_world

    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    scaffold_world(str(path_a), title="World A")
    scaffold_world(str(path_b), title="World A")
    result = json.loads(compare_worlds(str(path_a), str(path_b)))
    assert result["total_changes"] == 0


def test_compare_worlds_detects_change(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import scaffold_world

    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    scaffold_world(str(path_a), title="World A")
    scaffold_world(str(path_b), title="World B")  # different title
    result = json.loads(compare_worlds(str(path_a), str(path_b)))
    assert result["total_changes"] > 0
