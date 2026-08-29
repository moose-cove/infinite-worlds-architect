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
            "description": "",
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
            "description": "",
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
    """The pre-v2.4 bare-array shape must still resolve trigger IDs, and now errors on v2.4.

    Two regression guards in one. First: the old code gated on ``isinstance(data, list)``, so
    the v2.4 object shape silently skipped the ID lookup entirely — both shapes must reach it.
    Second: a world declaring v2.4 while carrying a v2.2 gate shape is self-contradictory, and
    the probe confirmed IW deletes the condition on import, so it is an error rather than a
    warning. The dangling-ID error must survive alongside the shape error, not replace it.
    """
    result = _validate(_world_with_gate_condition(ctype, ["DOES_NOT_EXIST"]))
    assert not result["valid"]
    assert any("DOES_NOT_EXIST" in e for e in result["errors"]), result["errors"]
    assert any("pre-v2.4 bare-array form" in e for e in result["errors"]), result["errors"]
    assert any(key in e for e in result["errors"]), result["errors"]
    assert not any("pre-v2.4 bare-array form" in w for w in result["warnings"]), result["warnings"]


@pytest.mark.parametrize(
    ("ctype", "key"),
    [("triggerPrereqs", "prereqs"), ("triggerBlockers", "blockers")],
)
def test_gate_condition_legacy_array_only_warns_below_v24(ctype, key):
    """A world that honestly declares a pre-v2.4 schemaVersion gets a warning, not an error.

    This is the contract that keeps ``example-world-schema-v2.1.json`` and
    ``example-world-schema-v2.2.json`` validating with warnings only (CLAUDE.md
    source-of-truth rule 1). Those two fixtures are the only regression coverage for reading
    the legacy gate shape at all, so an unconditional error here would delete that coverage.
    The message is identical at both severities — the author still learns the gate will be
    destroyed on import.
    """
    world = _world_with_gate_condition(ctype, ["DOES_NOT_EXIST"])
    world["schemaVersion"] = 2.2
    result = _validate(world)
    assert any("pre-v2.4 bare-array form" in w for w in result["warnings"]), result["warnings"]
    assert any(key in w for w in result["warnings"]), result["warnings"]
    assert not any("pre-v2.4 bare-array form" in e for e in result["errors"]), result["errors"]
    # The shape is advisory here, but a dangling reference is still a hard error.
    assert any("DOES_NOT_EXIST" in e for e in result["errors"]), result["errors"]


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


# ── Tracked item without `description` bricks the IW editor (bisected 2026-08-22) ──


def _world_with_tracked_item(**overrides) -> dict:
    world = _base_world()
    item = {
        "id": "TIDESC001",
        "name": "Clock",
        "description": "Turns elapsed.",
        "positionInList": 0,
        "dataType": "number",
        "variableName": "clock",
        "visibility": "everyone",
        "initialValue": "0",
        "autoUpdate": False,
    }
    item.update(overrides)
    world["trackedItems"] = [item]
    return world


def test_tracked_item_with_description_is_silent():
    result = _validate(_world_with_tracked_item())
    assert result["valid"], result["errors"]
    assert not any("'description'" in e for e in result["errors"])


def test_tracked_item_with_empty_description_is_silent():
    """An empty string is what the editor writes for a blank field — fine."""
    result = _validate(_world_with_tracked_item(description=""))
    assert result["valid"], result["errors"]


def test_tracked_item_without_description_errors():
    world = _world_with_tracked_item()
    del world["trackedItems"][0]["description"]
    result = _validate(world)
    assert not result["valid"]
    assert any("Clock" in e and "no 'description' key" in e for e in result["errors"]), result[
        "errors"
    ]


def test_tracked_item_with_null_description_errors():
    result = _validate(_world_with_tracked_item(description=None))
    assert not result["valid"]
    assert any("Clock" in e and "is null" in e for e in result["errors"]), result["errors"]


# ── Conditionless triggers never fire (confirmed in play 2026-08-22) ───────────


def _world_with_conditionless_trigger(**trigger_overrides) -> dict:
    """A one-trigger world with `triggerConditions: []` unless overridden."""
    world = _base_world()
    trigger = {
        "id": "TRIG0001",
        "name": "Clock",
        "canTriggerMoreThanOnce": True,
        "triggerEffects": [
            {
                "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                "type": "effectShowMessage",
                "data": "tick",
            }
        ],
        "triggerConditions": [],
    }
    trigger.update(trigger_overrides)
    world["triggerEvents"] = [trigger]
    return world


def test_empty_trigger_conditions_warns():
    """`triggerConditions: []` is a dead trigger, not an unconditional one — warn, don't error."""
    result = _validate(_world_with_conditionless_trigger())
    assert result["valid"], result["errors"]
    assert any("Clock" in w and "no triggerConditions" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_absent_trigger_conditions_warns():
    """An absent key has nothing to evaluate either; same warning (the cell itself is untested)."""
    world = _world_with_conditionless_trigger()
    del world["triggerEvents"][0]["triggerConditions"]
    result = _validate(world)
    assert any("Clock" in w and "no triggerConditions" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_sog_trigger_with_empty_conditions_does_not_warn():
    """`triggerOnStartOfGame: true` with `[]` fires at turn 0 (Probe D, 2026-08-22) — silent."""
    result = _validate(_world_with_conditionless_trigger(triggerOnStartOfGame=True))
    assert not any("no triggerConditions" in w for w in result["warnings"]), result["warnings"]


def test_trigger_with_a_condition_does_not_warn():
    world = _world_with_conditionless_trigger(
        triggerConditions=[
            {
                "id": "bbac5aa8-13cc-cc5a-f032-2016af92a391",
                "category": "condition",
                "type": "triggerOnPawScript",
                "data": "$game.turn_number >= 0",
            }
        ]
    )
    result = _validate(world)
    assert not any("no triggerConditions" in w for w in result["warnings"]), result["warnings"]


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
# a traceback to the caller.
#
# Every assertion below is written to fail if its SPECIFIC guard is removed. That is harder
# than it looks here, because the guards are layered: leaf-level type checks sit under an
# outer catch-all wrapper in validate_world, so "did it return a report" is satisfied by the
# wrapper even when the leaf guard is gone. Asserting only that would test nothing. Each test
# therefore pins the *mechanism*, not just the outcome.

_BACKSTOP_MESSAGE = "Semantic validation stopped on malformed world data"


@pytest.mark.parametrize(
    "value",
    [None, 5, "The marmut eats the marmalade", [1, 2, 3], {"a": 1}],
    ids=["null", "number", "bare-string", "list-of-non-strings", "object"],
)
def test_malformed_conditions_handled_by_its_own_guard(value):
    """`conditions` present but not a list[str].

    `world.get("conditions", [])` only defaults when the key is ABSENT, so an explicit
    `"conditions": null` used to raise TypeError straight out of validate_world. A bare
    string was worse than a crash — it iterated the string's characters and silently built
    garbage into the declared-event set.

    The load-bearing assertion is the LAST one. Returning a report is not enough: with the
    isinstance guard removed, the TypeError is still caught by validate_world's outer
    wrapper, so a report still comes back and a weaker test would pass. Asserting that the
    backstop message is *absent* proves the leaf guard did the work.
    """
    world = _base_world()
    world["conditions"] = value
    result = _validate(world)  # must not raise
    assert isinstance(result["errors"], list)
    assert isinstance(result["warnings"], list)
    assert not any(_BACKSTOP_MESSAGE in e for e in result["errors"]), (
        "conditions was handled by the outer catch-all rather than by the isinstance guard "
        f"in _check_event_conditions_registered: {result['errors']}"
    )


def test_non_dict_entity_entries_handled_by_its_own_guard():
    """A non-dict entry in an entity array crashed `_check_duplicate_ids`.

    That check runs first, so the crash pre-empted every later check — including their own
    isinstance guards, which were therefore unreachable on real malformed input.

    Note the placeholder values. An earlier version of this test used the string
    ``"not an object"`` and asserted that substring appeared in the errors — which passed
    even with the guard removed, because Tier 1's jsonschema message echoes the offending
    value back (``[trackedItems.0] 'not an object' is not of type 'object'``) and happened to
    contain the same words. The placeholders below are deliberately chosen to be absent from
    every message the validator can generate, and the assertion pins the guard's own format.
    """
    world = _base_world()
    world["trackedItems"] = ["placeholder-scalar"]
    world["NPCs"] = [42]
    result = _validate(world)
    assert not result["valid"]
    assert any("trackedItems: 1 entry/entries are not objects" in e for e in result["errors"]), (
        result["errors"]
    )
    assert any("NPCs: 1 entry/entries are not objects" in e for e in result["errors"]), result[
        "errors"
    ]
    assert not any(_BACKSTOP_MESSAGE in e for e in result["errors"]), (
        "sanitization did not cover every check that walks entity arrays; the outer "
        f"catch-all absorbed a crash instead: {result['errors']}"
    )


def test_non_dict_condition_and_effect_entries_are_sanitized():
    """The same hazard one level down, inside a trigger.

    `triggerConditions` / `triggerEffects` are walked about as widely as the top-level entity
    arrays, so they get the same treatment.
    """
    world = _base_world()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test Trigger",
            "triggerEffects": ["placeholder-scalar", 42],
            "triggerConditions": [7, None],
        }
    ]
    result = _validate(world)  # must not raise
    assert not any(_BACKSTOP_MESSAGE in e for e in result["errors"]), result["errors"]


def test_tier2_backstop_converts_unanticipated_exceptions_into_errors():
    """The outer wrapper around the Tier 2 block.

    This one cannot be reached by feeding `validate_world` a malformed world — the leaf
    guards intercept everything Tier 1 doesn't already reject, which is exactly what they
    are for. So the backstop is exercised by forcing a check to raise something no guard
    anticipates. Without the wrapper this propagates and `validate_world` raises instead of
    returning a report, breaking its documented contract.
    """
    from iw_architect import validator as validator_module

    def _boom(world, errors, warnings):
        raise RuntimeError("simulated unanticipated failure")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(validator_module, "_check_xml_deprecation", _boom)
        with pytest.raises(RuntimeError):
            # RuntimeError is deliberately NOT in the wrapper's except clause — the contract
            # covers malformed *data*, not arbitrary bugs, and swallowing every exception
            # would hide real defects. This documents where that line is drawn.
            _validate(_base_world())

    def _type_boom(world, errors, warnings):
        raise TypeError("simulated malformed-data failure")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(validator_module, "_check_xml_deprecation", _type_boom)
        result = _validate(_base_world())  # must not raise
    assert not result["valid"]
    assert any(_BACKSTOP_MESSAGE in e for e in result["errors"]), result["errors"]


def test_tier2_backstop_converts_recursion_errors_into_errors():
    """The `except RecursionError` arm of the Tier 2 wrapper.

    Split from the test above because the two `except` clauses are independently deletable,
    and a mutation removing only this one left the suite green. It needs a monkeypatch rather
    than a deep world: given the depth cap and the parser-level guard, no input reaching Tier 2
    can still blow the stack — which is the point, but it also means this arm is only
    observable by forcing it.
    """
    from iw_architect import validator as validator_module

    def _recursion_boom(world, errors, warnings):
        raise RecursionError("simulated stack exhaustion")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(validator_module, "_check_xml_deprecation", _recursion_boom)
        result = _validate(_base_world())  # must not raise
    assert not result["valid"]
    assert any("nested too deeply to analyze" in e for e in result["errors"]), result["errors"]


def _world_with_event_buried_at_depth(depth: int, event: str):
    """A world whose sole triggerOnEvent sits under `depth` nested `logic` combinators."""
    world = _base_world()
    world["conditions"] = []
    node = {"id": "cc-1", "category": "condition", "type": "triggerOnEvent", "data": event}
    for i in range(depth):
        node = {"id": f"lg-{i}", "category": "logic", "operator": "and", "data": [node]}
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Deep",
            "advancedLogic": True,
            "triggerEffects": [{"id": "aa-1", "type": "effectShowMessage", "data": "hi"}],
            "triggerConditions": [node],
        }
    ]
    return world


def test_condition_walk_descends_up_to_the_depth_cap():
    """Just under the cap, the walk still reaches the buried condition.

    Paired with the test below: this one proves the walker works at depth, so that the
    truncation assertion there cannot pass merely because the walker is broken.
    """
    from iw_architect.validator import _MAX_CONDITION_DEPTH

    world = _world_with_event_buried_at_depth(_MAX_CONDITION_DEPTH - 5, "shallow buried event")
    result = _validate(world)
    assert any("shallow buried event" in w for w in result["warnings"]), result["warnings"]


def test_condition_walk_stops_at_the_depth_cap():
    """Past the cap, the walk stops rather than recursing toward a stack overflow.

    Asserting *truncation* is what makes this test load-bearing. An earlier version nested
    300 levels and only asserted "a report came back" — which passed with the cap removed
    too, because 300 frames never approach CPython's recursion limit. The cap made no
    observable difference, so the test proved nothing.

    Note the layering: reached through `validate_world`'s file path, `json.loads` is actually
    the tighter constraint (its scanner recurses more per level than these walkers do), so a
    world deep enough to overflow the walkers fails to parse first and is reported as such.
    The cap therefore matters most for callers who hand an already-parsed dict to the check
    functions directly. Either way it must be observable, or it will be refactored away.
    """
    from iw_architect.validator import _MAX_CONDITION_DEPTH

    world = _world_with_event_buried_at_depth(_MAX_CONDITION_DEPTH + 50, "over-cap buried event")
    result = _validate(world)  # must not raise
    assert not any("over-cap buried event" in w for w in result["warnings"]), (
        "the condition walk descended past _MAX_CONDITION_DEPTH — the depth cap is not "
        f"limiting recursion: {result['warnings']}"
    )


def _world_with_dangling_prereq_at_depth(depth: int):
    """A world whose buried triggerPrereqs points at a trigger that does not exist."""
    world = _base_world()
    node = {
        "id": "cc-1",
        "category": "condition",
        "type": "triggerPrereqs",
        "data": {"prereqs": ["NOSUCHTRIGGER"], "firedThisTurn": False},
    }
    for i in range(depth):
        node = {"id": f"lg-{i}", "category": "logic", "operator": "and", "data": [node]}
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Deep",
            "advancedLogic": True,
            "triggerEffects": [{"id": "aa-1", "type": "effectShowMessage", "data": "hi"}],
            "triggerConditions": [node],
        }
    ]
    return world


def test_cross_reference_walk_descends_up_to_the_depth_cap():
    """`_check_cross_references` has its own walker and its own cap — cover it separately.

    Paired with the test below, exactly as the `_walk` pair above. Two walkers means two caps
    means two tests; a mutation removing only this one survived a suite that covered the other.
    """
    from iw_architect.validator import _MAX_CONDITION_DEPTH

    result = _validate(_world_with_dangling_prereq_at_depth(_MAX_CONDITION_DEPTH - 5))
    assert any("NOSUCHTRIGGER" in e for e in result["errors"]), result["errors"]


def test_cross_reference_walk_stops_at_the_depth_cap():
    """Past the cap the cross-reference walk stops, so the buried dangling ID goes unreported.

    This encodes a real trade-off rather than an unambiguous win: beyond
    ``_MAX_CONDITION_DEPTH`` a genuine broken reference is silently *not* checked. That is
    the accepted cost of never exhausting the stack, and the cap is set far past anything the
    IW editor can produce. If that judgment is ever revisited, this test is where the
    behaviour is written down.
    """
    from iw_architect.validator import _MAX_CONDITION_DEPTH

    result = _validate(_world_with_dangling_prereq_at_depth(_MAX_CONDITION_DEPTH + 50))
    assert not any("NOSUCHTRIGGER" in e for e in result["errors"]), (
        "the cross-reference walk descended past _MAX_CONDITION_DEPTH — its depth cap is "
        f"not limiting recursion: {result['errors']}"
    )


def test_unparseably_deep_world_reports_instead_of_crashing():
    """Nesting past what CPython's JSON scanner can parse is reported, not raised.

    Built as raw text: `json.dump` recurses per level too, so the test helper cannot write a
    file this deep.
    """
    from iw_architect.validator import validate_world

    inner = '{"id":"cc-1","category":"condition","type":"triggerOnEvent","data":"x"}'
    node = inner
    for i in range(5000):
        node = f'{{"id":"lg-{i}","category":"logic","operator":"and","data":[{node}]}}'
    world = _base_world()
    world["triggerEvents"] = []
    trigger = (
        '{"id":"TRIG0001","name":"Deep","advancedLogic":true,'
        '"triggerEffects":[{"id":"aa-1","type":"effectShowMessage","data":"hi"}],'
        f'"triggerConditions":[{node}]}}'
    )
    text = json.dumps(world).replace('"triggerEvents": []', f'"triggerEvents": [{trigger}]')
    tmp = tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False)
    tmp.write(text)
    tmp.close()
    try:
        result = json.loads(validate_world(tmp.name))  # must not raise
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    assert not result["valid"]
    assert any("too deep to parse" in e for e in result["errors"]), result["errors"]


# ── Duplicate IDs ─────────────────────────────────────────────────────────────


def test_duplicate_tracked_item_ids():
    world = _base_world()
    item = {
        "id": "DUPID1234",
        "name": "Health",
        "positionInList": 0,
        "dataType": "number",
        "description": "",
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
            "description": "",
            "visibility": "everyone",
            "autoUpdate": False,
        },
        {
            "id": "ITEM00002",
            "name": "Mana",
            "positionInList": 0,
            "dataType": "number",
            "description": "",
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
        "description": "",
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
        "description": "",
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
            "description": "",
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
        "description": "",
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
            "description": "",
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
    """rec 1: empty-string inequality is stripped on IW import → WARNING.

    ``textComparison`` is supplied so this isolates the inequality factor. Without it the
    condition would error on the missing key instead, and the test would pass for the wrong
    reason — which is exactly how Probe A's P6 confounded itself.
    """
    world = _trigger_world_with_condition(
        {
            "inequality": "",
            "requiredValue": "5",
            "trackedItemID": "ITEM00001",
            "textComparison": "contains",
        }
    )
    result = _validate(world)
    assert result["valid"], result["errors"]  # warning, not error
    assert any("inequality" in w and "silently stripped" in w for w in result["warnings"]), result[
        "warnings"
    ]


def test_empty_text_comparison_errors():
    """An empty-string textComparison costs the condition its existence → ERROR.

    Probe B's P6d: IW deleted the whole condition, not just the key. The previous wording
    ("silently stripped") described losing a field and was a warning; both were wrong.
    """
    world = _trigger_world_with_condition(
        {
            "inequality": "contains",
            "requiredValue": "cake",
            "trackedItemID": "ITEM00001",
            "textComparison": "",
        }
    )
    result = _validate(world)
    assert not result["valid"]
    assert any(
        "textComparison" in e and "deletes the whole condition" in e for e in result["errors"]
    ), result["errors"]


def test_missing_text_comparison_errors():
    """An absent textComparison is as fatal as an empty one → ERROR.

    Probe B's P6b used ``at_least`` — a fixture-proven inequality — with no ``textComparison``
    at all, and IW still deleted the condition. That is what isolated the fatal factor to the
    missing key rather than to ``not_equal``, which round-tripped intact whenever the key was
    present (P6a).
    """
    world = _trigger_world_with_condition(
        {"inequality": "at_least", "requiredValue": "1", "trackedItemID": "ITEM00001"}
    )
    result = _validate(world)
    assert not result["valid"]
    assert any("textComparison" in e and "missing" in e for e in result["errors"]), result["errors"]


def test_not_equal_with_text_comparison_is_accepted():
    """``not_equal`` is not the problem — it round-trips intact when textComparison is set.

    Probe B's P6a. The KB carried ``not_equal`` as [PENDING TEST] for import survival since
    May 2026; this pins the confirmed result so a future tightening cannot quietly re-flag it.
    """
    world = _trigger_world_with_condition(
        {
            "inequality": "not_equal",
            "requiredValue": "99",
            "trackedItemID": "ITEM00001",
            "textComparison": "contains",
        }
    )
    result = _validate(world)
    assert result["valid"], result["errors"]
    assert not any("textComparison" in e for e in result["errors"]), result["errors"]


# ── schema v2.4: per-character tracked-item override scope ───────────────────


def _world_with_initial_tracked_item_value(
    based_on_pc: str, value, item_scope: str = "player"
) -> dict:
    """A world whose one character carries one initialTrackedItemValues entry."""
    world = _base_world()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Probe Item",
            "positionInList": 0,
            "dataType": "text",
            "description": "",
            "visibility": "everyone",
            "autoUpdate": False,
            "initialValueBasedOnPC": item_scope,
            "variableName": "probe_item",
        }
    ]
    world["possibleCharacters"] = [
        {
            "name": "Probe Subject",
            "characterId": "CHAR0001",
            "initialTrackedItemValues": [
                {
                    "id": "ITEM00001",
                    "name": "Probe Item",
                    "visibility": "everyone",
                    "initialPCValue": value,
                    "initialValueBasedOnPC": based_on_pc,
                }
            ],
        }
    ]
    return world


@pytest.mark.parametrize(
    ("value", "shape"),
    [("PLAIN", "string"), (["A", "B", "C"], "array")],
    ids=["string", "array"],
)
def test_player_scoped_initial_tracked_item_value_errors(value, shape):
    """Probe B's P10b/P10c: ``"player"`` deletes the entry on import, at any value shape.

    Parametrized over both shapes because the pre-probe hypothesis blamed the array form.
    The 2x2 showed a clean main effect on ``initialValueBasedOnPC`` with no interaction, so
    both shapes must fail identically — a check that only caught the array would reproduce
    the wrong theory.
    """
    result = _validate(_world_with_initial_tracked_item_value("player", value))
    assert not result["valid"], shape
    assert any(
        "initialValueBasedOnPC 'player'" in e and "deletes the entry" in e for e in result["errors"]
    ), result["errors"]
    # The error and the doomed-entry warning are mutually exclusive branches: a
    # player-scoped entry must never ALSO draw the backed-by-player-item warning.
    assert not any("backed by a tracked item" in w for w in result["warnings"]), result["warnings"]


@pytest.mark.parametrize(
    ("value", "shape"),
    [("PLAIN", "string"), (["A", "B", "C"], "array")],
    ids=["string", "array"],
)
def test_character_scoped_initial_tracked_item_value_is_accepted(value, shape):
    """Probe B's P10a/P10d controls: ``"character"`` survives at either value shape.

    The array cell matters most — it is the combination the canonical fixture demonstrates,
    so flagging it would break real authoring. Item scoped ``"character"`` too — the pairing
    the canonical fixture and editor-authored worlds carry — so this must be silent in
    warnings as well.
    """
    result = _validate(
        _world_with_initial_tracked_item_value("character", value, item_scope="character")
    )
    assert not any("initialValueBasedOnPC" in e for e in result["errors"]), (
        shape,
        result["errors"],
    )
    assert not any("initialValueBasedOnPC" in w for w in result["warnings"]), (
        shape,
        result["warnings"],
    )


def test_player_scoped_entry_on_character_scoped_item_still_errors():
    """Probe E's decisive PE2 cell: entry ``"player"`` + item ``"character"`` was DELETED.

    Import keys the delete on the incoming ENTRY's own scope value, whatever the backing
    item says — the cell Probe B could not separate. Confirmed 2026-08-28 by
    probes/probe-e-scope-q10.json vs probe-e-imported.json.
    """
    result = _validate(
        _world_with_initial_tracked_item_value("player", "PLAIN", item_scope="character")
    )
    assert not result["valid"]
    assert any(
        "initialValueBasedOnPC 'player'" in e and "deletes the entry" in e for e in result["errors"]
    ), result["errors"]


def test_entry_backed_by_player_scoped_item_warns_as_doomed():
    """Probe E's PE1 cell: entry ``"character"`` + item ``"player"`` survives ONE import.

    But IW rewrites entry scopes to the item's on export, so the next round trip deletes
    it (probe-e-imported.json carries the rewritten "player" scope; probe-e-imported-2.json
    shows the entry gone). Not an error — the first import genuinely keeps it — but the
    author must hear that the state is non-round-trippable.
    """
    result = _validate(_world_with_initial_tracked_item_value("character", "PLAIN"))
    assert result["valid"], result["errors"]
    assert any(
        "backed by a tracked item" in w and "round trip silently deletes it" in w
        for w in result["warnings"]
    ), result["warnings"]


@pytest.mark.parametrize(
    ("item_scope", "entry_id_suffix"),
    [("same", ""), ("character", ""), ("player", "MISSING")],
    ids=["item-same", "item-character", "unresolvable-item-id"],
)
def test_doomed_entry_warning_only_fires_on_player_scoped_backing_items(
    item_scope, entry_id_suffix
):
    """The warning is scoped to a resolvable, player-scoped backing item — nothing else.

    Pins the silent cells: item ``"same"`` (never probed, no evidence of harm), item
    ``"character"`` (the normal pairing), and an entry whose ``id`` resolves to no tracked
    item at all (``item_scopes.get`` must miss quietly, not warn or crash).
    """
    world = _world_with_initial_tracked_item_value("character", "PLAIN", item_scope=item_scope)
    if entry_id_suffix:
        entry = world["possibleCharacters"][0]["initialTrackedItemValues"][0]
        entry["id"] = entry["id"] + entry_id_suffix
    result = _validate(world)
    assert not any("backed by a tracked item" in w for w in result["warnings"]), result["warnings"]


# ── textComparison: "unset" has more spellings than absent-or-empty ──────────


@pytest.mark.parametrize(
    "tc",
    [None, "   ", 0, False, [], {}],
    ids=["null", "whitespace", "zero", "false", "empty-list", "empty-dict"],
)
def test_non_string_text_comparison_errors(tc):
    """Every non-string (and whitespace-only) textComparison is the fatal shape.

    ``null`` is the one that matters: it is the most natural JSON spelling of "unset" and is
    semantically identical to the absent key Probe B proved fatal. An earlier version of this
    rule tested only ``"textComparison" not in data`` plus ``== ""``, so ``null``, ``0``,
    ``false``, ``[]`` and ``"   "`` all validated clean.
    """
    world = _trigger_world_with_condition(
        {
            "inequality": "at_least",
            "requiredValue": "1",
            "trackedItemID": "ITEM00001",
            "textComparison": tc,
        }
    )
    result = _validate(world)
    assert not result["valid"], tc
    assert any(
        "textComparison" in e and "deletes the whole condition" in e for e in result["errors"]
    ), result["errors"]


def test_flat_shaped_condition_still_checked_for_text_comparison():
    """A condition carrying its fields flat, with no ``data`` key, must not skip the rule.

    ``_check_cross_references`` already resolves ``trackedItemID`` as
    ``data.get(...) or cond.get(...)``, so the flat shape is one the codebase expects to meet.
    Reading only ``data`` let it bypass the check entirely — and a flat condition has no
    ``textComparison`` in ``data`` by definition, which is exactly the deleted-on-import shape.
    """
    world = _trigger_world_with_condition({})
    # Drop the `data` key entirely, leaving the flat fields the helper already sets.
    del world["triggerEvents"][0]["triggerConditions"][0]["data"]
    result = _validate(world)
    assert not result["valid"]
    assert any("textComparison" in e for e in result["errors"]), result["errors"]


@pytest.mark.parametrize(
    "entries",
    [None, 5, "oops", {"a": 1}, [None], [["x"]]],
    ids=["null", "int", "string", "dict", "list-of-null", "list-of-list"],
)
def test_malformed_initial_tracked_item_values_does_not_halt_validation(entries):
    """Tier 2 runs on worlds that have already failed Tier 1, so it must not raise on garbage.

    ``possibleCharacters`` is sanitized upstream; the nested ``initialTrackedItemValues`` is
    not. A non-list there used to raise TypeError, which ``validate_world`` catches — but the
    catch aborts every remaining Tier 2 check, so one malformed key silently disabled the rest
    of semantic validation.
    """
    world = _base_world()
    world["possibleCharacters"] = [
        {"name": "C", "characterId": "CHAR0001", "initialTrackedItemValues": entries}
    ]
    result = _validate(world)
    assert not any("Semantic validation stopped" in e for e in result["errors"]), result["errors"]


# ── gate-shape severity keys off declared schemaVersion ──────────────────────


@pytest.mark.parametrize(
    ("version", "expect_error"),
    [
        (2.4, True),
        (2.5, True),
        (3, True),
        (2.2, False),
        (2.1, False),
        (None, False),
        (True, False),
        ("2.4", False),
    ],
    ids=["2.4", "2.5", "3", "2.2", "2.1", "absent", "bool-true", "string"],
)
def test_legacy_gate_severity_by_schema_version(version, expect_error):
    """A legacy bare-array gate errors at v2.4+ and warns below, with the fallbacks pinned.

    ``bool-true`` is the one worth naming: ``bool`` is a subclass of ``int``, so a refactor to
    ``float(raw or 0)`` would read ``true`` as version 1.0 and pass every other case here.
    ``string`` and ``absent`` both fall back to warn — the lenient direction, since Tier 1
    already reports a non-numeric schemaVersion as a type error.
    """
    world = _base_world()
    if version is None:
        world.pop("schemaVersion", None)
    else:
        world["schemaVersion"] = version
    world["triggerEvents"] = [
        {"id": "TRIG0001", "name": "Anchor", "triggerEffects": []},
        {
            "id": "TRIG0002",
            "name": "Gated",
            "triggerEffects": [],
            "triggerConditions": [
                {
                    "id": "ccac5aa8-13cc-cc5a-f032-2016af92a391",
                    "category": "condition",
                    "type": "triggerPrereqs",
                    "data": ["TRIG0001"],
                }
            ],
        },
    ]
    result = _validate(world)
    errs = [e for e in result["errors"] if "bare-array" in e]
    warns = [w for w in result["warnings"] if "bare-array" in w]
    if expect_error:
        assert errs and not warns, (version, result["errors"], result["warnings"])
    else:
        assert warns and not errs, (version, result["errors"], result["warnings"])


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
            "description": "",
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
            "description": "",
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
            "description": "",
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
        "description": "",
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
            "description": "",
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


# ── triggerOnPawScript conditions (fixture 1.09) ─────────────────────────────

_MISSING = object()


def _pawscript_condition_world(
    data,
    tracked_items: list[dict],
    *,
    nested: bool = False,
    ctype: str = "triggerOnPawScript",
) -> dict:
    """A world with one trigger gated by a PawScript-expression condition.

    ``ctype`` selects the condition type (``triggerOnPawScript`` by default, or
    ``triggerOnRandomChance``). ``nested=True`` wraps the condition inside an ``and``
    logic node so the walker's recursion into ``category: "logic"`` trees is exercised.
    """
    world = _base_world()
    world["trackedItems"] = tracked_items
    cond = {
        "id": "e95ded8d-1a55-d946-f9a9-22b65f99886d",
        "category": "condition",
        "type": ctype,
    }
    if data is not _MISSING:
        cond["data"] = data
    conditions = (
        [{"id": "logic-1", "category": "logic", "operator": "and", "data": [cond]}]
        if nested
        else [cond]
    )
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "PawScript Gate",
            "advancedLogic": nested,
            "triggerConditions": conditions,
            "triggerEffects": [
                {
                    "id": "aaac5aa8-13cc-cc5a-f032-2016af92a391",
                    "type": "effectShowMessage",
                    "data": "Lemon it is.",
                }
            ],
        }
    ]
    return world


def test_pawscript_condition_is_a_known_type():
    # Registered condition type — must NOT trip the "unknown condition type" warning,
    # and a well-formed expression over a real variableName produces no
    # triggerOnPawScript warning at all.
    world = _pawscript_condition_world(
        '$favorite_flavor = "Lemon"', [_yaml_item(variable_name="favorite_flavor")]
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("unknown condition type" in w for w in result["warnings"]), result["warnings"]
    assert not any("triggerOnPawScript" in w for w in result["warnings"]), result["warnings"]


def test_pawscript_condition_undeclared_variable_warns():
    # A $root that is not a variableName / native → WARNING; the real one and the
    # $player native are not flagged.
    world = _pawscript_condition_world(
        '$favourite_flavor = "Lemon" and $player.name != ""',
        [_yaml_item(variable_name="favorite_flavor")],
    )
    result = _validate(world)
    assert result["valid"]
    hits = [w for w in result["warnings"] if "triggerOnPawScript references" in w]
    assert len(hits) == 1 and "$favourite_flavor" in hits[0], result["warnings"]
    assert not any("references $player" in w for w in hits)


def test_pawscript_condition_nested_in_logic_is_checked():
    world = _pawscript_condition_world(
        "$nope = 1", [_yaml_item(variable_name="favorite_flavor")], nested=True
    )
    result = _validate(world)
    assert any("triggerOnPawScript references $nope" in w for w in result["warnings"]), result[
        "warnings"
    ]


@pytest.mark.parametrize("data", [_MISSING, "", "   "])
def test_pawscript_condition_blank_data_errors(data):
    # Probe C (2026-08-29) imported both shapes: a missing `data` key had its condition
    # deleted outright, and a blank string errored at runtime every turn. Either way the
    # trigger is silently dead, so these are errors rather than warnings.
    world = _pawscript_condition_world(data, [_yaml_item(variable_name="favorite_flavor")])
    result = _validate(world)
    assert not result["valid"]
    hits = [e for e in result["errors"] if "triggerOnPawScript data is" in e]
    assert len(hits) == 1 and "never fires" in hits[0], result["errors"]


@pytest.mark.parametrize("data", [None, 5, {"expr": "$x = 1"}])
def test_pawscript_condition_non_string_data_warns(data):
    # A present-but-not-a-string `data` is clearly malformed, but Probe C did not probe
    # that shape — so it stays a warning rather than joining the errors above.
    world = _pawscript_condition_world(data, [_yaml_item(variable_name="favorite_flavor")])
    result = _validate(world)
    assert result["valid"]
    assert any(
        "triggerOnPawScript data is" in w and "non-empty expression" in w
        for w in result["warnings"]
    ), result["warnings"]
    assert not any("triggerOnPawScript" in e for e in result["errors"])


def test_pawscript_interpolation_warns():
    # Probe C: IW substitutes the item's VALUE into the text before parsing, so
    # `<<probe_flavor>> = "Lemon"` was evaluated as `Lemon = "Lemon"` and errored. Warn
    # rather than error — a numeric value would substitute into a valid comparison.
    world = _pawscript_condition_world(
        '<<favorite_flavor>> = "Lemon"', [_yaml_item(variable_name="favorite_flavor")]
    )
    result = _validate(world)
    assert result["valid"]
    hits = [w for w in result["warnings"] if "interpolation" in w]
    assert len(hits) == 1 and "$favorite_flavor" in hits[0], result["warnings"]


@pytest.mark.parametrize("expr", ["$favorite_flavor", "  $favorite_flavor  ", "$favorite_flavor.n"])
def test_pawscript_bare_handle_warns(expr):
    # Probe C: `$probe_flavor` "worked out to Lemon, not true or false", so a condition
    # that is only a value reference can never fire.
    world = _pawscript_condition_world(expr, [_yaml_item(variable_name="favorite_flavor")])
    result = _validate(world)
    assert result["valid"]
    assert any("bare value reference" in w for w in result["warnings"]), result["warnings"]


@pytest.mark.parametrize(
    "expr",
    [
        '$favorite_flavor = "Lemon"',
        "not $favorite_flavor",
        '$favorite_flavor.item("rex").exists()',
        "$favorite_flavor > 0 and $player.name != ''",
    ],
)
def test_pawscript_boolean_expressions_are_not_flagged_as_bare(expr):
    # The bare-handle check must not fire on anything carrying an operator, keyword or
    # call — those can all evaluate to true/false.
    world = _pawscript_condition_world(expr, [_yaml_item(variable_name="favorite_flavor")])
    result = _validate(world)
    assert not any("bare value reference" in w for w in result["warnings"]), result["warnings"]


def test_random_chance_bare_handle_is_silent():
    # A bare $handle is the CORRECT form for a chance formula (Probe D #8 — it fired and
    # the value drove the roll), so the bare-handle warning is triggerOnPawScript-only.
    world = _pawscript_condition_world(
        "$number_of_non_human_friends",
        [_yaml_item(variable_name="number_of_non_human_friends")],
        ctype="triggerOnRandomChance",
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("bare value reference" in w for w in result["warnings"]), result["warnings"]


# ── triggerOnRandomChance formulas referencing tracked items (fixture 1.1) ───────


@pytest.mark.parametrize(
    "formula",
    [
        "30",
        "15+round(turn_number%random)",
        # The fixture 1.1 sample: a tracked item read as $variableName, with the bare
        # `turn_number` / `random` tokens of the random-chance dialect left unchecked.
        "$number_of_non_human_friends+round(turn_number%random)",
    ],
)
def test_random_chance_formula_well_formed_is_silent(formula):
    world = _pawscript_condition_world(
        formula,
        [_yaml_item(variable_name="number_of_non_human_friends")],
        ctype="triggerOnRandomChance",
    )
    result = _validate(world)
    assert result["valid"]
    assert not any("triggerOnRandomChance" in w for w in result["warnings"]), result["warnings"]


def test_random_chance_formula_undeclared_variable_warns():
    world = _pawscript_condition_world(
        "$number_of_nonhuman_friends+round(turn_number%random)",
        [_yaml_item(variable_name="number_of_non_human_friends")],
        ctype="triggerOnRandomChance",
    )
    result = _validate(world)
    assert result["valid"]
    hits = [w for w in result["warnings"] if "triggerOnRandomChance references" in w]
    assert len(hits) == 1 and "$number_of_nonhuman_friends" in hits[0], result["warnings"]


def test_random_chance_formula_nested_in_logic_is_checked():
    world = _pawscript_condition_world(
        "$nope+5",
        [_yaml_item(variable_name="number_of_non_human_friends")],
        nested=True,
        ctype="triggerOnRandomChance",
    )
    result = _validate(world)
    assert any("triggerOnRandomChance references $nope" in w for w in result["warnings"]), result[
        "warnings"
    ]


@pytest.mark.parametrize("data", [_MISSING, "", "   ", None, 30, {"chance": 30}])
def test_random_chance_non_string_data_warns(data):
    # The schema types the formula as a string; anything else is warn-only (never an
    # error) until a probe shows how IW treats it. Probe C escalated the blank/missing
    # case for triggerOnPawScript only — the random-chance equivalent is still untested.
    world = _pawscript_condition_world(
        data,
        [_yaml_item(variable_name="number_of_non_human_friends")],
        ctype="triggerOnRandomChance",
    )
    result = _validate(world)
    assert result["valid"]
    assert any(
        "triggerOnRandomChance data is" in w and "non-empty expression" in w
        for w in result["warnings"]
    ), result["warnings"]
    assert not any("triggerOnRandomChance" in e for e in result["errors"])
