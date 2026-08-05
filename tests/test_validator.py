"""Validator negative tests.

For each error class in the design brief §4.6, a fixture that triggers the error
must cause validate_world to report it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


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
    from iw_architect.tools.helpers import create_new_world_json

    # NamedTemporaryFile(delete=False) instead of mktemp() — mktemp has a TOCTOU race.
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        create_new_world_json(tmp_path, title="Test World")
        world = json.loads(Path(tmp_path).read_text())
    finally:
        Path(tmp_path).unlink(missing_ok=True)
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
                    "data": {"prereqs": ["DOES_NOT_EXIST"], "firedThisTurn": False},
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
                    "data": {"blockers": ["DOES_NOT_EXIST"], "firedThisTurn": False},
                }
            ],
        }
    ]
    result = _validate(world)
    assert not result["valid"]
    assert any("DOES_NOT_EXIST" in e for e in result["errors"])


# ── schema v2.4: gate-condition data shape (triggerPrereqs / triggerBlockers) ──


def _world_with_gate_condition(ctype: str, data):
    """A one-trigger world whose sole condition is `ctype` carrying `data`."""
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
                    "type": ctype,
                    "data": data,
                }
            ],
        }
    ]
    return world


@pytest.mark.parametrize(
    ("ctype", "key"),
    [("triggerPrereqs", "prereqs"), ("triggerBlockers", "blockers")],
)
def test_gate_condition_legacy_array_still_cross_checked(ctype, key):
    """The pre-v2.4 bare-array shape must still resolve trigger IDs, with a warning.

    Regression guard: the old code gated on ``isinstance(data, list)``, so the v2.4 object
    shape silently skipped the check entirely. Both shapes must reach the same lookup.
    """
    result = _validate(_world_with_gate_condition(ctype, ["DOES_NOT_EXIST"]))
    assert not result["valid"]
    assert any("DOES_NOT_EXIST" in e for e in result["errors"])
    assert any("pre-v2.4 bare-array form" in w for w in result["warnings"]), result["warnings"]
    assert any(key in w for w in result["warnings"]), result["warnings"]


@pytest.mark.parametrize("ctype", ["triggerPrereqs", "triggerBlockers"])
@pytest.mark.parametrize("data", ["TRIG0001", None, 7, True], ids=["str", "null", "int", "bool"])
def test_gate_condition_scalar_data_is_an_error(ctype, data):
    """`data` that is neither the v2.4 object nor a legacy array is an error, not a skip.

    Silently skipping is the failure mode this whole change exists to prevent, so an
    unrecognized shape must be loud.
    """
    result = _validate(_world_with_gate_condition(ctype, data))
    assert not result["valid"]
    assert any("must be an object" in e for e in result["errors"]), result["errors"]


@pytest.mark.parametrize(
    ("ctype", "key"),
    [("triggerPrereqs", "prereqs"), ("triggerBlockers", "blockers")],
)
def test_gate_condition_object_missing_id_list_is_an_error(ctype, key):
    result = _validate(_world_with_gate_condition(ctype, {"firedThisTurn": True}))
    assert not result["valid"]
    assert any(f"missing the '{key}' list" in e for e in result["errors"]), result["errors"]


@pytest.mark.parametrize("ctype", ["triggerPrereqs", "triggerBlockers"])
def test_gate_condition_missing_fired_this_turn_warns(ctype):
    """A well-formed object with no `firedThisTurn` is valid but worth flagging."""
    key = "prereqs" if ctype == "triggerPrereqs" else "blockers"
    result = _validate(_world_with_gate_condition(ctype, {key: ["TRIG0001"]}))
    assert result["valid"], result["errors"]
    assert any("no boolean 'firedThisTurn'" in w for w in result["warnings"]), result["warnings"]


# ── schema v2.4: triggerOnEvent ↔ top-level `conditions` registry ──────────────


def _world_with_event_condition(event: str, declared: list[str] | None):
    world = _base_world()
    if declared is not None:
        world["conditions"] = declared
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
                    "type": "triggerOnEvent",
                    "data": event,
                }
            ],
        }
    ]
    return world


def test_trigger_on_event_not_in_conditions_registry_warns():
    """An undeclared event still evaluates, so this is a warning — never an error."""
    result = _validate(_world_with_event_condition("The marmot eats the marmalade", []))
    assert result["valid"], result["errors"]
    assert any(
        "not declared in the world's top-level 'conditions' registry" in w
        for w in result["warnings"]
    ), result["warnings"]


def test_trigger_on_event_declared_in_conditions_registry_is_silent():
    event = "The marmot eats the marmalade"
    result = _validate(_world_with_event_condition(event, [event]))
    assert result["valid"], result["errors"]
    assert not any("not declared in the top-level" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_conditions_entry_with_no_matching_trigger_on_event_warns():
    """The reverse direction: a declared event nothing uses.

    Under the registry reading that's a dead entry in the editor's dropdown; under the
    competing derived-index reading it's stale data. Worth surfacing either way.
    """
    result = _validate(_world_with_event_condition("Used event", ["Used event", "Orphan event"]))
    assert result["valid"], result["errors"]
    assert any(
        "'Orphan event' is not used by any triggerOnEvent" in w for w in result["warnings"]
    ), result["warnings"]


def test_trigger_on_event_count_over_cap_warns():
    """The documented world-level cap of 10 AI-evaluated events.

    Wiki-corroborated rather than fixture-proven, so it warns and is deliberately NOT encoded
    as `maxItems` in the JSON Schema — a Tier 1 error would be too strong for the evidence.
    """
    events = [f"Event number {i}" for i in range(11)]
    world = _world_with_event_condition(events[0], events)
    result = _validate(world)
    assert result["valid"], result["errors"]
    assert any("documented cap is 10" in w for w in result["warnings"]), result["warnings"]


def test_trigger_on_event_count_at_cap_is_silent():
    """Exactly 10 is fine — the cap is inclusive."""
    events = [f"Event number {i}" for i in range(10)]
    result = _validate(_world_with_event_condition(events[0], events))
    assert not any("documented cap" in w for w in result["warnings"]), result["warnings"]


def test_trigger_on_event_nested_in_logic_condition_is_still_checked():
    """Advanced-logic triggers nest conditions under a `logic` combinator — recurse into it."""
    world = _base_world()
    world["conditions"] = []
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
                    "data": [
                        {
                            "id": "ccac5aa8-13cc-cc5a-f032-2016af92a391",
                            "category": "condition",
                            "type": "triggerOnEvent",
                            "data": "A buried event",
                        }
                    ],
                }
            ],
        }
    ]
    result = _validate(world)
    assert any("A buried event" in w for w in result["warnings"]), result["warnings"]


# ── validate_world always returns a report, never raises ──────────────────────
#
# `validate_world` is an MCP tool whose docstring promises a JSON report with 'valid',
# 'errors' and 'warnings'. A malformed world must surface as errors in that report, never as
# a traceback to the caller. Every case below crashed before the guards were added.


@pytest.mark.parametrize(
    "value",
    [None, 5, "The marmut eats the marmalade", [1, 2, 3], {"a": 1}],
    ids=["null", "number", "bare-string", "list-of-non-strings", "object"],
)
def test_malformed_conditions_reports_instead_of_crashing(value):
    """`conditions` present but not a list[str].

    `world.get("conditions", [])` only defaults when the key is ABSENT, so an explicit
    `"conditions": null` used to raise TypeError straight out of validate_world. A bare
    string was worse than a crash — it iterated the string's characters and silently built
    garbage into the declared-event set.
    """
    world = _base_world()
    world["conditions"] = value
    result = _validate(world)  # must not raise
    assert isinstance(result["errors"], list)
    assert isinstance(result["warnings"], list)


def test_non_dict_entity_entries_report_instead_of_crashing():
    """A non-dict entry in an entity array crashed `_check_duplicate_ids`.

    That check runs first, so the crash pre-empted every later check — including their own
    isinstance guards, which were therefore unreachable on real malformed input.
    """
    world = _base_world()
    world["trackedItems"] = ["not an object"]
    world["NPCs"] = [42]
    result = _validate(world)
    assert not result["valid"]
    assert any("not an object" in e for e in result["errors"]), result["errors"]


def test_deeply_nested_logic_conditions_report_instead_of_crashing():
    """Author-controlled nesting depth must not exhaust the Python stack.

    `category: "logic"` nests recursively, and three separate walkers descend it. Past
    _MAX_CONDITION_DEPTH the walk stops; past CPython's own limit the JSON parser gives up
    first. Either way the caller gets a report.

    Depth is 300: comfortably past _MAX_CONDITION_DEPTH (100) so the walkers' guards are the
    thing under test, while staying inside what ``json.dump`` can serialize — the test helper
    writes the world to disk, and the encoder recurses per level too.
    """
    world = _base_world()
    node = {
        "id": "cc-1",
        "category": "condition",
        "type": "triggerOnEvent",
        "data": "a deeply buried event",
    }
    for i in range(300):
        node = {"id": f"lg-{i}", "category": "logic", "operator": "and", "data": [node]}
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Deep",
            "advancedLogic": True,
            "triggerEffects": [
                {"id": "aa-1", "type": "effectShowMessage", "data": "hi"},
            ],
            "triggerConditions": [node],
        }
    ]
    result = _validate(world)  # must not raise
    assert isinstance(result["errors"], list)


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


def test_non_unique_position_in_list_mixed_types_does_not_crash():
    # Regression: duplicate positions of unorderable mixed types (null + number)
    # must not crash the validator's sort — it should still report the dupe.
    # Previously `sorted({None, 1})` raised TypeError and took down validate_world.
    base = {
        "id": "ITEM00001",
        "name": "A",
        "positionInList": None,
        "dataType": "number",
        "visibility": "everyone",
        "autoUpdate": False,
    }
    world = _base_world()
    world["trackedItems"] = [
        base,
        {**base, "id": "ITEM00002", "name": "B", "positionInList": None},
        {**base, "id": "ITEM00003", "name": "C", "positionInList": 1},
        {**base, "id": "ITEM00004", "name": "D", "positionInList": 1},
    ]
    # Must not raise; the report is still produced.
    result = _validate(world)
    assert not result["valid"]
    assert any("non-unique positionInList" in e for e in result["errors"])


def test_non_unique_position_in_list_unhashable_does_not_crash():
    # Regression: duplicated UNHASHABLE positionInList values (dict/list) must not
    # crash the dedup step — a plain set() raises "unhashable type: 'dict'". The
    # dupe is still reported.
    base = {
        "id": "ITEM00001",
        "name": "A",
        "positionInList": {"x": 1},
        "dataType": "number",
        "visibility": "everyone",
        "autoUpdate": False,
    }
    world = _base_world()
    world["trackedItems"] = [
        base,
        {**base, "id": "ITEM00002", "name": "B", "positionInList": {"x": 1}},
    ]
    # Must not raise.
    result = _validate(world)
    assert not result["valid"]
    assert any("non-unique positionInList" in e for e in result["errors"])


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

    fixture = Path(__file__).parent.parent / "example-world-schema-v2.4.json"
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


# ── Tracked-item ID charset warnings ──────────────────────────────────────────


def _make_tracked_item(id_: str, name: str, position: int) -> dict:
    return {
        "id": id_,
        "name": name,
        "positionInList": position,
        "dataType": "number",
        "visibility": "everyone",
        "autoUpdate": False,
    }


def test_tracked_item_non_alphanumeric_id_warns():
    """A tracked-item id with '+' or '/' triggers a WARNING (not an error).

    IW silently renames such IDs on import without updating trigger references,
    leaving dangling refs — confirmed via import test (June 2026).
    """
    world = _base_world()
    world["trackedItems"] = [_make_tracked_item("bad+id12", "Health", 0)]
    result = _validate(world)
    assert result["valid"], (
        "Non-alphanumeric tracked-item id should warn, not error. Errors: " + str(result["errors"])
    )
    assert any("bad+id12" in w and "alphanumeric" in w.lower() for w in result["warnings"]), (
        f"Expected alphanumeric warning for 'bad+id12'. Warnings: {result['warnings']}"
    )


def test_tracked_item_slash_id_warns():
    """A tracked-item id containing '/' also triggers the charset warning."""
    world = _base_world()
    world["trackedItems"] = [_make_tracked_item("trkSlsh/2", "Mana", 0)]
    result = _validate(world)
    assert result["valid"]
    assert any("trkSlsh/2" in w for w in result["warnings"]), (
        f"Expected warning for 'trkSlsh/2'. Warnings: {result['warnings']}"
    )


def test_tracked_item_clean_id_no_charset_warning():
    """A tracked-item id that is purely alphanumeric must not trigger the charset warning."""
    world = _base_world()
    world["trackedItems"] = [_make_tracked_item("trkClean3", "Stamina", 0)]
    result = _validate(world)
    assert result["valid"]
    assert not any("alphanumeric" in w.lower() and "trkClean3" in w for w in result["warnings"]), (
        f"Unexpected charset warning for clean id. Warnings: {result['warnings']}"
    )


def test_eib_non_alphanumeric_id_does_not_warn():
    """Instruction-block IDs with '+' or '/' must NOT trigger a charset warning.

    EIB/KIB/trigger IDs with '+' or '/' were observed to survive IW import unchanged
    in the same test where tracked-item IDs were silently renamed. Scoping the warning
    to tracked items only prevents false positives on other entity kinds.
    """
    world = _base_world()
    world["instructionBlocks"] = [
        {
            "id": "eibPlus+6",
            "name": "Test EIB",
            "positionInList": 0,
            "content": "Some content",
        }
    ]
    result = _validate(world)
    # May have other errors (e.g. schema validation on EIB shape) but must not warn on charset
    assert not any("eibPlus+6" in w and "alphanumeric" in w.lower() for w in result["warnings"]), (
        f"Unexpected charset warning for EIB id. Warnings: {result['warnings']}"
    )


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


def _trigger_world_with_effect(
    effect_type: str, effect_data: dict | str | None, sog: bool = False
) -> dict:
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


def test_effect_present_choice_non_dict_data_warns():
    # rec 3: non-dict effectPresentChoice data is also malformed → WARNING
    world = _trigger_world_with_effect("effectPresentChoice", "not a dict")
    result = _validate(world)
    assert result["valid"]
    assert any("effectPresentChoice" in w and "not a dict" in w for w in result["warnings"]), (
        result["warnings"]
    )


def test_effect_request_input_non_dict_data_warns():
    # rec 3: non-dict effectRequestInput data is also malformed → WARNING
    world = _trigger_world_with_effect("effectRequestInput", None)
    result = _validate(world)
    assert result["valid"]
    assert any("effectRequestInput" in w and "not a dict" in w for w in result["warnings"]), result[
        "warnings"
    ]


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


def test_empty_skills_with_hide_skill_system_warns():
    # rec 6: empty skills + hideSkillSystem: true → still valid, but emits the
    # hideSkillSystem-specific caveat warning (not the generic empty-skills one).
    world = _base_world(skills=[], hideSkillSystem=True)
    result = _validate(world)
    assert result["valid"]
    assert any("skills" in w and "hideSkillSystem" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_scaffold_skills_not_empty(tmp_path):
    # rec 6: scaffold must seed at least one skill
    from iw_architect.tools.helpers import create_new_world_json

    output = tmp_path / "scaffold_skills.json"
    create_new_world_json(str(output), title="Test World")
    world = json.loads(output.read_text())
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


# ── schema v2.2: PawScript + YAML tracked items ──────────────────────────────


def _yaml_item(variable_name: str = "puppies", **overrides) -> dict:
    """A minimal dataType='yaml' tracked item, with a variableName for PawScript."""
    item = {
        "id": "ITEM00001",
        "name": "Puppies",
        "positionInList": 0,
        "dataType": "yaml",
        "visibility": "everyone",
        "autoUpdate": False,
        "variableName": variable_name,
    }
    item.update(overrides)
    return item


def _script_world(script: str, tracked_items: list[dict]) -> dict:
    """A world with one effectRunScript trigger carrying the given PawScript body."""
    world = _base_world()
    world["trackedItems"] = tracked_items
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Script Trigger",
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectRunScript",
                    "data": script,
                }
            ],
        }
    ]
    return world


def test_variable_name_bad_format_warns():
    # A variableName that is not snake_case → WARNING
    world = _base_world()
    world["trackedItems"] = [_yaml_item(variable_name="BadName")]
    result = _validate(world)
    assert result["valid"]
    assert any("variableName" in w and "BadName" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_variable_name_duplicate_warns():
    # Two tracked items sharing a variableName → WARNING
    world = _base_world()
    world["trackedItems"] = [
        _yaml_item(variable_name="dup"),
        _yaml_item(variable_name="dup", id="ITEM00002", name="Kittens", positionInList=1),
    ]
    result = _validate(world)
    assert result["valid"]
    assert any("Duplicate" in w and "dup" in w for w in result["warnings"]), result["warnings"]


def test_pawscript_undeclared_variable_warns():
    # A $root that is not a variableName / native / loop var → WARNING
    world = _script_world(
        "$puppies.count += 1\n$unknown_var = 5",
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert result["valid"]
    assert any(
        "unknown_var" in w and "effectRunScript references" in w for w in result["warnings"]
    ), result["warnings"]
    # The real variableName must NOT be flagged.
    assert not any(
        "$puppies" in w and "effectRunScript references" in w for w in result["warnings"]
    ), result["warnings"]


def test_pawscript_loop_variable_not_flagged():
    # A `for each` loop variable is locally bound and must NOT warn.
    world = _script_world(
        "for each $p in $puppies\n  $p.friendliness += 1",
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("effectRunScript references" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_pawscript_set_variable_not_flagged():
    # A `set $x = ...` scratch variable is locally bound and must NOT warn.
    world = _script_world(
        "set $total = 0\nfor each $p in $puppies\n  set $total = $total + $p.friendliness",
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("effectRunScript references" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_pawscript_set_to_native_warns():
    # `set $player = ...` reuses a reserved read-only native as a set variable → WARNING.
    world = _script_world(
        'set $player = "Bob"',
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert any("set $player" in w and "reserved read-only" in w for w in result["warnings"]), (
        result["warnings"]
    )


def test_pawscript_comment_lines_ignored():
    # `#` comment lines (e.g. containing URLs) must not contribute identifiers.
    world = _script_world(
        "# see https://infiniteworlds.app/pawscript-reference for $syntax\n$puppies.count += 1",
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("effectRunScript references" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_pawscript_write_to_native_warns():
    # Assigning to $player (a read-only native) → WARNING
    world = _script_world(
        '$player.name = "Bob"',
        [_yaml_item(variable_name="puppies")],
    )
    result = _validate(world)
    assert result["valid"]
    assert any("player" in w and "read-only" in w for w in result["warnings"]), result["warnings"]


def test_enforce_format_without_schema_warns():
    # enforceFormat true with an empty formatSchema → WARNING
    world = _base_world()
    world["trackedItems"] = [_yaml_item(enforceFormat=True, formatSchema="")]
    result = _validate(world)
    assert result["valid"]
    assert any("enforceFormat" in w and "formatSchema" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_enforce_format_with_schema_no_warning():
    # enforceFormat true with a non-empty formatSchema → no warning
    world = _base_world()
    world["trackedItems"] = [_yaml_item(enforceFormat=True, formatSchema="- name: text\n  ...:")]
    result = _validate(world)
    assert not any("enforceFormat" in w and "formatSchema" in w for w in result["warnings"]), (
        result["warnings"]
    )


def test_yaml_invalid_initial_value_errors():
    # dataType 'yaml' with an unparseable initialValue → ERROR
    world = _base_world()
    world["trackedItems"] = [_yaml_item(initialValue="foo: [1, 2")]  # unclosed flow sequence
    result = _validate(world)
    assert not result["valid"]
    assert any("initialValue" in e and "YAML" in e for e in result["errors"]), result["errors"]


def test_yaml_valid_initial_value_no_error():
    # dataType 'yaml' with parseable YAML → no YAML error
    world = _base_world()
    world["trackedItems"] = [_yaml_item(initialValue="- name: Spot\n  friendliness: 5")]
    result = _validate(world)
    assert not any("YAML" in e for e in result["errors"]), result["errors"]


def test_yaml_deeply_nested_does_not_crash():
    # Regression: pathologically deep YAML must be reported as invalid, not crash
    # the validator with an uncaught RecursionError (PyYAML is not depth-limited,
    # even under safe_load).
    import sys

    depth = sys.getrecursionlimit() + 5000
    deep = "[" * depth + "]" * depth
    world = _base_world()
    world["trackedItems"] = [_yaml_item(initialValue=deep)]
    # Must not raise.
    result = _validate(world)
    assert any("initialValue" in e and "YAML" in e for e in result["errors"]), result["errors"]


def test_xml_datatype_deprecation_warns():
    # dataType 'xml' → deprecation WARNING (never an error)
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Grudges",
            "positionInList": 0,
            "dataType": "xml",
            "visibility": "everyone",
            "autoUpdate": False,
        }
    ]
    result = _validate(world)
    assert result["valid"]  # deprecation is a warning, not an error
    assert any("xml" in w.lower() and "deprecated" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_effect_run_script_no_unknown_effect_warning():
    # effectRunScript must be registered — no "unknown effect type" warning
    world = _script_world("$puppies.count += 1", [_yaml_item(variable_name="puppies")])
    result = _validate(world)
    assert not any("effectRunScript" in w and "unknown" in w for w in result["warnings"]), result[
        "warnings"
    ]
