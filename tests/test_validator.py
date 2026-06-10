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

    from iw_architect.tools.helpers import create_new_world_json

    tmp = tempfile.mktemp(suffix=".json")
    create_new_world_json(tmp, title="Test World")
    world = json.loads(Path(tmp).read_text())
    Path(tmp).unlink(missing_ok=True)
    world.update(overrides)
    return world


# ── Null image fields ────────────────────────────────────────────────────────


def test_null_image_style_warns_but_is_valid():
    # imageStyle is the one image field the schema tolerates as null: it warns
    # (not recommended) but does not error.
    world = _base_world(imageStyle=None)
    result = _validate(world)
    assert any("imageStyle" in w and "null" in w for w in result["warnings"])
    assert not any("imageStyle" in e for e in result["errors"])
    assert result["valid"]


def test_null_image_model_errors():
    # Sibling image fields stay string-only: null is a Tier 1 error, not a warning.
    world = _base_world(imageModel=None)
    result = _validate(world)
    assert not result["valid"]
    assert any("imageModel" in e for e in result["errors"])
    assert not any("imageModel" in w for w in result["warnings"])


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


def test_confirm_path_relative_rejected():
    """A relative path is rejected with an actionable error rather than silently
    resolved against the server process's (wrong) working directory."""
    from iw_architect.tools.helpers import confirm_path

    result = json.loads(confirm_path("worlds/foo.json"))
    assert result["status"] == "error"
    assert result["is_absolute"] is False
    assert result["input_path"] == "worlds/foo.json"
    assert "relative" in result["message"].lower()


def test_confirm_path_tilde_is_absolute(tmp_path, monkeypatch):
    """A leading ``~`` expands to an absolute path, so it is accepted (not rejected
    as relative)."""
    from iw_architect.tools.helpers import confirm_path

    monkeypatch.setenv("HOME", str(tmp_path))
    result = json.loads(confirm_path("~/probe_world.json"))
    assert result["status"] == "ok"
    assert result["resolved_path"] == str(tmp_path / "probe_world.json")


def test_validate_world_relative_rejected():
    """The same absolute-path guard applies to validate_world, not just confirm_path."""
    from iw_architect.validator import validate_world

    result = json.loads(validate_world("worlds/foo.json"))
    assert result["valid"] is False
    assert any("relative" in e.lower() for e in result["errors"])


def test_read_world_field_relative_rejected():
    from iw_architect.tools.inspection import read_world_field

    result = json.loads(read_world_field("worlds/foo.json", "title"))
    assert "relative" in result["error"].lower()


def test_audit_world_relative_rejected():
    from iw_architect.tools.analysis import audit_world

    result = json.loads(audit_world("worlds/foo.json"))
    assert "relative" in result["error"].lower()


def test_create_new_world_json_relative_rejected():
    from iw_architect.tools.helpers import create_new_world_json

    result = json.loads(create_new_world_json("worlds/foo.json"))
    assert "relative" in result["error"].lower()


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
    from iw_architect.tools.helpers import create_new_world_json

    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    create_new_world_json(str(path_a), title="World A")
    create_new_world_json(str(path_b), title="World A")
    result = json.loads(compare_worlds(str(path_a), str(path_b)))
    assert result["total_changes"] == 0


def test_compare_worlds_detects_change(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    create_new_world_json(str(path_a), title="World A")
    create_new_world_json(str(path_b), title="World B")  # different title
    result = json.loads(compare_worlds(str(path_a), str(path_b)))
    assert result["total_changes"] > 0


# ── KB v2.8 checks (recs 1–7 + rec 9 validator slice) ───────────────────────


def _trigger_world_with_condition(cond_data: dict) -> dict:
    """Helper: world with a single triggerOnTrackedItem condition carrying the given data."""
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
                    "type": "triggerOnTrackedItem",
                    "trackedItemID": "ITEM00001",
                    "inequality": cond_data.get("inequality", "is_exactly"),
                    "data": cond_data,
                }
            ],
        }
    ]
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
        }
    ]
    return world


def _trigger_world_with_effect(effect_type: str, effect_data, sog: bool = False) -> dict:
    """Helper: world with a trigger carrying a single effect."""
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerOnStartOfGame": sog,
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": effect_type,
                    "data": effect_data,
                }
            ],
        }
    ]
    return world


# ── rec 1: empty-string condition strip ──────────────────────────────────────


def test_empty_inequality_warns():
    # rec 1: empty-string inequality silently stripped on IW import → WARNING
    world = _trigger_world_with_condition(
        {"inequality": "", "requiredValue": "5", "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    assert result["valid"]  # warning, not error
    assert any("inequality" in w and "silently stripped" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_empty_text_comparison_warns():
    # rec 1: empty-string textComparison silently stripped on IW import → WARNING
    world = _trigger_world_with_condition(
        {
            "inequality": "contains",
            "requiredValue": "cake",
            "trackedItemID": "ITEM00001",
            "textComparison": "",
        }
    )
    result = _validate(world)
    assert result["valid"]
    assert any("textComparison" in w and "silently stripped" in w for w in result["warnings"]), (
        result["warnings"]
    )


# ── rec 2: non-string requiredValue ──────────────────────────────────────────


def test_non_string_required_value_errors():
    # rec 2: int requiredValue → AttributeError on IW import → ERROR
    world = _trigger_world_with_condition(
        {"inequality": "is_exactly", "requiredValue": 5, "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    assert not result["valid"]
    assert any("requiredValue" in e and "string" in e for e in result["errors"]), result["errors"]


def test_float_required_value_errors():
    # rec 2: float requiredValue also crashes IW → ERROR
    world = _trigger_world_with_condition(
        {"inequality": "at_least", "requiredValue": 5.5, "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    assert not result["valid"]
    assert any("requiredValue" in e for e in result["errors"]), result["errors"]


def test_string_required_value_is_valid():
    # rec 2: string requiredValue is fine
    world = _trigger_world_with_condition(
        {"inequality": "is_exactly", "requiredValue": "5", "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    assert not any("requiredValue" in e for e in result["errors"]), result["errors"]


# ── rec 3: player-interaction effect shapes ───────────────────────────────────


def test_effect_present_choice_missing_keys_warns():
    # rec 3: effectPresentChoice missing required keys → WARNING
    world = _trigger_world_with_effect(
        "effectPresentChoice",
        # Missing: selectionMode, minSelections, maxSelections, updateMode,
        # valueDelimiter, targetTrackedItemId
        {"message": "Choose one:", "choices": "A\nB"},
    )
    result = _validate(world)
    assert result["valid"]
    assert any("effectPresentChoice" in w and "missing" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_effect_present_choice_all_keys_valid():
    # rec 3: effectPresentChoice with all 8 keys → no warning
    world = _trigger_world_with_effect(
        "effectPresentChoice",
        {
            "message": "Choose one:",
            "choices": "A\nB",
            "selectionMode": "single",
            "minSelections": None,
            "maxSelections": None,
            "updateMode": "replace",
            "valueDelimiter": "newline",
            "targetTrackedItemId": "",
        },
    )
    result = _validate(world)
    assert not any("effectPresentChoice" in w and "missing" in w for w in result["warnings"]), (
        result["warnings"]
    )


def test_effect_request_input_missing_keys_warns():
    # rec 3: effectRequestInput missing required keys → WARNING
    world = _trigger_world_with_effect(
        "effectRequestInput",
        # Missing: targetTrackedItemId, requiresInput, inputMode
        {"requestText": "Tell me your name:"},
    )
    result = _validate(world)
    assert result["valid"]
    assert any("effectRequestInput" in w and "missing" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_effect_request_input_all_keys_valid():
    # rec 3: effectRequestInput with all 4 keys → no missing-keys warning
    world = _trigger_world_with_effect(
        "effectRequestInput",
        {
            "requestText": "Tell me your name:",
            "targetTrackedItemId": "",
            "requiresInput": True,
            "inputMode": "single",
        },
    )
    result = _validate(world)
    assert not any("effectRequestInput" in w and "missing" in w for w in result["warnings"]), (
        result["warnings"]
    )


# ── rec 4: effectFireRandomTrigger registered ────────────────────────────────


def test_effect_fire_random_trigger_no_unknown_warning():
    # rec 4: effectFireRandomTrigger must not produce "unknown effect type" warning
    world = _trigger_world_with_effect("effectFireRandomTrigger", None)
    result = _validate(world)
    assert not any("effectFireRandomTrigger" in w and "unknown" in w for w in result["warnings"]), (
        result["warnings"]
    )


# ── rec 5: visibility + inequality ───────────────────────────────────────────


def test_hidden_boring_visibility_valid():
    # rec 5: hidden_boring is a valid visibility value
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "hidden_boring",
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert result["valid"], result["errors"]
    assert not any("visibility" in e for e in result["errors"])


def test_not_equal_inequality_no_cross_ref_error():
    # rec 5: not_equal inequality in triggerOnTrackedItem → no unknown-inequality error
    world = _trigger_world_with_condition(
        {"inequality": "not_equal", "requiredValue": "5", "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    # Should not error on the inequality value (the schema now includes not_equal)
    assert not any("not_equal" in e for e in result["errors"]), result["errors"]


# ── rec 6: skills not empty ───────────────────────────────────────────────────


def test_empty_skills_warns():
    # rec 6: empty skills array → WARNING
    world = _base_world(skills=[])
    result = _validate(world)
    assert result["valid"]
    assert any("skills" in w and "empty" in w for w in result["warnings"]), result["warnings"]


def test_non_empty_skills_no_warning():
    # rec 6: non-empty skills → no empty-skills warning
    world = _base_world(skills=["General"])
    result = _validate(world)
    assert not any("skills" in w and "empty" in w for w in result["warnings"]), result["warnings"]


def test_scaffold_skills_not_empty():
    # rec 6: scaffold must seed at least one skill
    import tempfile

    from iw_architect.tools.helpers import create_new_world_json

    tmp = tempfile.mktemp(suffix=".json")
    create_new_world_json(tmp, title="Test World")
    world = json.loads(Path(tmp).read_text())
    Path(tmp).unlink(missing_ok=True)
    assert isinstance(world["skills"], list)
    assert len(world["skills"]) >= 1, "scaffold must seed at least one skill string"


# ── rec 7: SoG effect context ─────────────────────────────────────────────────


def test_sog_only_effect_in_regular_trigger_warns():
    # rec 7: effectChangeBackground in a non-SoG trigger → WARNING
    world = _trigger_world_with_effect("effectChangeBackground", "New background", sog=False)
    result = _validate(world)
    assert result["valid"]
    assert any(
        "effectChangeBackground" in w and "Start-of-Game" in w for w in result["warnings"]
    ), result["warnings"]


def test_sog_only_effect_in_sog_trigger_valid():
    # rec 7: effectChangeBackground in a SoG trigger → no SoG warning
    world = _trigger_world_with_effect("effectChangeBackground", "New background", sog=True)
    result = _validate(world)
    assert not any(
        "effectChangeBackground" in w and "Start-of-Game" in w for w in result["warnings"]
    ), result["warnings"]


def test_regular_only_effect_in_sog_trigger_warns():
    # rec 7: effectGiveInfo in a SoG trigger → WARNING
    world = _trigger_world_with_effect("effectGiveInfo", "Some info", sog=True)
    result = _validate(world)
    assert result["valid"]
    assert any("effectGiveInfo" in w and "stripped" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_regular_only_effect_in_regular_trigger_valid():
    # rec 7: effectGiveInfo in a regular trigger → no SoG warning
    world = _trigger_world_with_effect("effectGiveInfo", "Some info", sog=False)
    result = _validate(world)
    assert not any("effectGiveInfo" in w and "stripped" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_fire_random_trigger_in_sog_warns():
    # rec 7: effectFireRandomTrigger in SoG trigger → WARNING
    world = _trigger_world_with_effect("effectFireRandomTrigger", None, sog=True)
    result = _validate(world)
    assert result["valid"]
    assert any("effectFireRandomTrigger" in w and "stripped" in w for w in result["warnings"]), (
        result["warnings"]
    )


def test_effect_change_first_action_in_regular_trigger_warns():
    # rec 7: effectChangeFirstAction in a non-SoG trigger → WARNING
    world = _trigger_world_with_effect("effectChangeFirstAction", "New first action", sog=False)
    result = _validate(world)
    assert result["valid"]
    assert any(
        "effectChangeFirstAction" in w and "Start-of-Game" in w for w in result["warnings"]
    ), result["warnings"]


# ── rec 9: effectSetTrackedItemValue replaceWith ─────────────────────────────


def test_set_tracked_item_value_missing_replace_with_warns():
    # rec 9: effectSetTrackedItemValue without replaceWith → WARNING
    world = _trigger_world_with_effect(
        "effectSetTrackedItemValue",
        {"action": "set", "newValue": "10", "trackedItemID": "ITEM00001"},
    )
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert result["valid"]
    assert any("replaceWith" in w for w in result["warnings"]), result["warnings"]


def test_set_tracked_item_value_with_replace_with_no_warning():
    # rec 9: effectSetTrackedItemValue with replaceWith present → no replaceWith warning
    world = _trigger_world_with_effect(
        "effectSetTrackedItemValue",
        {"action": "set", "newValue": "10", "replaceWith": "", "trackedItemID": "ITEM00001"},
    )
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert not any("replaceWith" in w for w in result["warnings"]), result["warnings"]
