"""Tests for audit_world, compare_worlds, and get_diff_summary."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent.parent / "example-world-schema-v2.1.json"


def _write(world: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False)
    json.dump(world, tmp)
    tmp.flush()
    return tmp.name


def _base() -> dict:
    from iw_architect.tools.helpers import create_new_world_json

    tmp = tempfile.mktemp(suffix=".json")
    create_new_world_json(tmp, title="Test")
    world = json.loads(Path(tmp).read_text())
    Path(tmp).unlink(missing_ok=True)
    return world


# ── audit_world ───────────────────────────────────────────────────────────────


def test_audit_returns_findings():
    from iw_architect.tools.analysis import audit_world

    result = json.loads(audit_world(str(FIXTURE_PATH)))
    assert "findings" in result
    assert any(f["type"] == "token_budget" for f in result["findings"])


def test_audit_detects_trigger_cycle(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Trigger A",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "cond-uuid-1111-1111-1111-111111111111",
                    "category": "condition",
                    "type": "triggerPrereqs",
                    "data": ["TRIG0002"],
                },
            ],
        },
        {
            "id": "TRIG0002",
            "name": "Trigger B",
            "triggerEffects": [
                {
                    "id": "eff-uuid-2222-2222-2222-222222222222",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "cond-uuid-2222-2222-2222-222222222222",
                    "category": "condition",
                    "type": "triggerPrereqs",
                    "data": ["TRIG0001"],
                },
            ],
        },
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        cycle_findings = [f for f in result["findings"] if f["type"] == "trigger_cycle"]
        assert len(cycle_findings) >= 1
        assert cycle_findings[0]["severity"] == "error"
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_no_cycle_finding(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Trigger A",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
        },
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        ok_findings = [f for f in result["findings"] if f["type"] == "trigger_graph"]
        assert any(f["severity"] == "ok" for f in ok_findings)
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_detects_npc_name_in_instructions(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["instructions"] = "The world is guarded by Elara the wizard."
    world["NPCs"] = [{"id": "NPC000001", "name": "Elara", "positionInList": 0}]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        overlap = [f for f in result["findings"] if f["type"] == "npc_instruction_overlap"]
        assert len(overlap) == 1
        assert "Elara" in overlap[0]["npcs"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_detects_empty_instruction_block(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["instructionBlocks"] = [{"id": "IB000001A", "name": "Empty Block", "content": "hi"}]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        short = [f for f in result["findings"] if f["type"] == "empty_instruction_blocks"]
        assert len(short) == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_detects_unconditioned_trigger(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Always Fires",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        uncond = [f for f in result["findings"] if f["type"] == "unconditioned_triggers"]
        assert len(uncond) == 1
        assert "Always Fires" in uncond[0]["triggers"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_triggerOnStartOfGame_not_flagged_as_unconditioned(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Start Trigger",
            "triggerOnStartOfGame": True,
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        uncond = [f for f in result["findings"] if f["type"] == "unconditioned_triggers"]
        assert len(uncond) == 0
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_heavy_section_warns(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["instructions"] = "A" * 5000  # ~1250 tokens
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        heavy = [f for f in result["findings"] if f["type"] == "token_budget_warning"]
        assert len(heavy) == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_missing_per_character_overrides(tmp_path):
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
            "initialValueBasedOnPC": "character",
        }
    ]
    world["possibleCharacters"] = [
        {
            "name": "Alice",
            "characterId": "CHAR0001",
            "skills": {},
            "initialTrackedItemValues": [],  # missing override for ITEM00001
        }
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        missing = [f for f in result["findings"] if f["type"] == "missing_per_character_overrides"]
        assert len(missing) >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def _menu_world(
    initial_pc_value, *, nest_in_logic: bool = False, top_level_id: bool = True
) -> dict:
    """Build a world with one tracked item, one character override carrying
    ``initial_pc_value``, and a triggerOnTrackedItem condition on that item.

    When ``nest_in_logic`` is True the condition is wrapped in a compound
    ``category: "logic"`` group to exercise recursive descent. When
    ``top_level_id`` is False the leaf carries ``trackedItemID`` only inside
    ``data`` (not at the top level), exercising the fallback lookup.
    """
    leaf = {
        "id": "cond-uuid-1111-1111-1111-1111-111111111111",
        "category": "condition",
        "type": "triggerOnTrackedItem",
        "data": {
            "inequality": "is_exactly",
            "requiredValue": "Basic Images",
            "trackedItemID": "ITEM00001",
            "textComparison": "contains",
        },
    }
    if top_level_id:
        leaf["trackedItemID"] = "ITEM00001"
    if nest_in_logic:
        conditions = [
            {
                "id": "cond-uuid-9999-9999-9999-999999999999",
                "category": "logic",
                "operator": "and",
                "data": [leaf],
            }
        ]
    else:
        conditions = [leaf]

    world = _base()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Image Settings",
            "positionInList": 0,
            "dataType": "text",
            "visibility": "everyone",
            "autoUpdate": False,
            "initialValueBasedOnPC": "character",
        }
    ]
    world["possibleCharacters"] = [
        {
            "name": "Alice",
            "characterId": "CHAR0001",
            "skills": {},
            "initialTrackedItemValues": [
                {
                    "id": "ITEM00001",
                    "name": "Image Settings",
                    "visibility": "everyone",
                    "initialPCValue": initial_pc_value,
                    "initialValueBasedOnPC": "character",
                }
            ],
        }
    ]
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Images",
            "triggerOnStartOfGame": True,
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": conditions,
        }
    ]
    return world


def test_audit_detects_menu_backed_condition(tmp_path):
    """A triggerOnTrackedItem condition on a pick-one menu item is surfaced as info."""
    from iw_architect.tools.analysis import audit_world

    world = _menu_world(["Basic Images", "Premium Advanced Images"])
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        menu = [f for f in result["findings"] if f["type"] == "menu_backed_condition"]
        assert len(menu) == 1
        assert menu[0]["severity"] == "info"
        assert menu[0]["trackedItem"] == "Image Settings"
        assert menu[0]["options"] == ["Basic Images", "Premium Advanced Images"]
        # The detail must spell out that the test is not always-true.
        assert "not always-true" in menu[0]["detail"].lower()
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_menu_backed_condition_not_flagged_for_scalar(tmp_path):
    """A scalar initialPCValue is a fixed value, not a menu — no finding."""
    from iw_architect.tools.analysis import audit_world

    world = _menu_world("Basic Images")
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        menu = [f for f in result["findings"] if f["type"] == "menu_backed_condition"]
        assert menu == []
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_menu_backed_condition_nested_in_logic(tmp_path):
    """A menu-backed condition nested inside a compound logic group is still detected."""
    from iw_architect.tools.analysis import audit_world

    world = _menu_world(["Basic Images", "Premium Advanced Images"], nest_in_logic=True)
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        menu = [f for f in result["findings"] if f["type"] == "menu_backed_condition"]
        assert len(menu) == 1
        assert menu[0]["trackedItem"] == "Image Settings"
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_menu_backed_condition_id_only_in_data(tmp_path):
    """The trackedItemID may live only inside the condition's data dict."""
    from iw_architect.tools.analysis import audit_world

    world = _menu_world(["Basic Images", "Premium Advanced Images"], top_level_id=False)
    # Sanity: the top-level key really is absent on the leaf.
    assert "trackedItemID" not in world["triggerEvents"][0]["triggerConditions"][0]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        menu = [f for f in result["findings"] if f["type"] == "menu_backed_condition"]
        assert len(menu) == 1
        assert menu[0]["trackedItem"] == "Image Settings"
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_menu_backed_options_unioned_across_characters(tmp_path):
    """Options offered by different characters for the same item are unioned, deduped, ordered."""
    from iw_architect.tools.analysis import audit_world

    world = _menu_world(["Basic Images", "Premium Advanced Images"])
    # A second character offers an overlapping-plus-new menu for the same item.
    world["possibleCharacters"].append(
        {
            "name": "Bob",
            "characterId": "CHAR0002",
            "skills": {},
            "initialTrackedItemValues": [
                {
                    "id": "ITEM00001",
                    "name": "Image Settings",
                    "visibility": "everyone",
                    "initialPCValue": ["Premium Advanced Images", "Ultra Images"],
                    "initialValueBasedOnPC": "character",
                }
            ],
        }
    )
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        menu = [f for f in result["findings"] if f["type"] == "menu_backed_condition"]
        assert len(menu) == 1
        assert menu[0]["options"] == [
            "Basic Images",
            "Premium Advanced Images",
            "Ultra Images",
        ]
    finally:
        Path(path).unlink(missing_ok=True)


def test_audit_file_not_found():
    from iw_architect.tools.analysis import audit_world

    result = json.loads(audit_world("/nonexistent/world.json"))
    assert "error" in result


# ── compare_worlds ────────────────────────────────────────────────────────────


def test_compare_worlds_scalar_change(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a), title="Original")
    create_new_world_json(str(b), title="Modified")

    result = json.loads(compare_worlds(str(a), str(b)))
    assert result["total_changes"] > 0
    paths = [c["path"] for c in result["changes"]]
    assert any("title" in p for p in paths)


def test_compare_worlds_entity_added(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a))
    create_new_world_json(str(b))

    world_b = json.loads(b.read_text())
    world_b["NPCs"] = [{"id": "NPC000001", "name": "Bob", "positionInList": 0}]
    b.write_text(json.dumps(world_b))

    result = json.loads(compare_worlds(str(a), str(b)))
    assert any(c["type"] == "added" for c in result["changes"])


def test_compare_worlds_missing_file_a(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    b = tmp_path / "b.json"
    create_new_world_json(str(b))
    result = json.loads(compare_worlds("/nonexistent.json", str(b)))
    assert "error" in result


def test_compare_worlds_missing_file_b(tmp_path):
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    create_new_world_json(str(a))
    result = json.loads(compare_worlds(str(a), "/nonexistent.json"))
    assert "error" in result


# ── get_diff_summary ──────────────────────────────────────────────────────────


def test_get_diff_summary_no_changes(tmp_path):
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    create_new_world_json(str(a), title="Same")
    result = get_diff_summary(str(a), str(a))
    assert "No differences" in result


def test_get_diff_summary_with_changes(tmp_path):
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a), title="Original")
    create_new_world_json(str(b), title="Changed")

    result = get_diff_summary(str(a), str(b))
    assert "## Changes" in result
    assert "change" in result.lower()


def test_get_diff_summary_missing_original(tmp_path):
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    b = tmp_path / "b.json"
    create_new_world_json(str(b))
    result = get_diff_summary("/nonexistent.json", str(b))
    assert "Error" in result


def test_get_diff_summary_missing_current(tmp_path):
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    create_new_world_json(str(a))
    result = get_diff_summary(str(a), "/nonexistent.json")
    assert "Error" in result


def test_get_diff_summary_entity_added(tmp_path):
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a))
    create_new_world_json(str(b))

    world_b = json.loads(b.read_text())
    world_b["NPCs"] = [{"id": "NPC000001", "name": "Bob", "positionInList": 0}]
    b.write_text(json.dumps(world_b))

    result = get_diff_summary(str(a), str(b))
    assert "Added" in result


# ── Additional validator coverage ─────────────────────────────────────────────


def test_validate_set_tracked_item_unknown_ref(tmp_path):
    """effectSetTrackedItemValue with unknown trackedItemID raises error."""
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectSetTrackedItemValue",
                    "data": {
                        "action": "set",
                        "newValue": "x",
                        "replaceWith": "",
                        "trackedItemID": "BADID0001",
                    },
                    "trackedItemID": "BADID0001",
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert not result["valid"]
        assert any("BADID0001" in e for e in result["errors"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_effect_present_choice_unknown_tracked_item(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectPresentChoice",
                    "data": {
                        "choices": "A\nB",
                        "message": "Pick",
                        "updateMode": "replace",
                        "maxSelections": None,
                        "minSelections": None,
                        "selectionMode": "single",
                        "valueDelimiter": "newline",
                        "targetTrackedItemId": "BADITEM01",
                    },
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert not result["valid"]
        assert any("BADITEM01" in e for e in result["errors"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_effect_request_input_unknown_tracked_item(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectRequestInput",
                    "data": {
                        "inputMode": "multi",
                        "requestText": "Enter text",
                        "requiresInput": True,
                        "targetTrackedItemId": "BADITEM01",
                    },
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert not result["valid"]
        assert any("BADITEM01" in e for e in result["errors"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_unknown_effect_type_is_warning(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectSomeFutureType",
                    "data": "data",
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]
        assert any("effectSomeFutureType" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_unknown_condition_type_is_warning(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "cond-uuid-1111-1111-1111-1111-111111111111",
                    "category": "condition",
                    "type": "triggerOnFuturePlatformType",
                    "data": "x",
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]
        assert any("triggerOnFuturePlatformType" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_template_variable_undeclared_warns(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["instructions"] = "The player has <<undeclared_variable>> health."
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]
        assert any("undeclared_variable" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_template_variable_tracked_item_is_ok(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
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
    world["instructions"] = "The player has <<health>> health."
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        # No warning about <<health>>
        assert not any("health" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_older_schema_version_warns(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["schemaVersion"] = 1.0
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]
        assert any("older" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_file_not_found():
    from iw_architect.validator import validate_world

    result = json.loads(validate_world("/nonexistent/world.json"))
    assert not result["valid"]
    assert any("not found" in e for e in result["errors"])


def test_validate_invalid_json(tmp_path):
    from iw_architect.validator import validate_world

    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {{{")
    result = json.loads(validate_world(str(bad)))
    assert not result["valid"]
    assert any("Invalid JSON" in e for e in result["errors"])


def test_validate_effect_modify_keyword_block_unknown_id(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectModifyKeywordBlock",
                    "data": {"id": "NONEXISTENT", "content": "new", "keywords": ["kw"]},
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert not result["valid"]
        assert any("NONEXISTENT" in e for e in result["errors"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_defeat_condition_alreadyfired_warns(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["defeatCondition"] = {
        "condition": "player dies",
        "text": "Game over.",
        "alreadyFired": True,
    }
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]  # warning, not error
        assert any("alreadyFired" in w for w in result["warnings"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_trigger_on_tracked_item_unknown_ref(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "cond-uuid-1111-1111-1111-1111-111111111111",
                    "category": "condition",
                    "type": "triggerOnTrackedItem",
                    "data": {
                        "inequality": "at_least",
                        "requiredValue": "5",
                        "trackedItemID": "UNKNOWN01",
                        "textComparison": "contains",
                    },
                    "inequality": "at_least",
                    "trackedItemID": "UNKNOWN01",
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert not result["valid"]
        assert any("UNKNOWN01" in e for e in result["errors"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_validate_trigger_on_tracked_item_skill_ref_is_ok(tmp_path):
    from iw_architect.validator import validate_world

    world = _base()
    world["skills"] = ["Patience"]
    world["triggerEvents"] = [
        {
            "id": "TRIG0001",
            "name": "Test",
            "triggerEffects": [
                {
                    "id": "eff-uuid-1111-1111-1111-1111-111111111111",
                    "type": "effectShowMessage",
                    "data": "hi",
                }
            ],
            "triggerConditions": [
                {
                    "id": "cond-uuid-1111-1111-1111-1111-111111111111",
                    "category": "condition",
                    "type": "triggerOnTrackedItem",
                    "data": {
                        "inequality": "at_least",
                        "requiredValue": "3",
                        "trackedItemID": "skill_patience",
                        "textComparison": "contains",
                    },
                    "inequality": "at_least",
                    "trackedItemID": "skill_patience",
                }
            ],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(validate_world(path))
        assert result["valid"]
    finally:
        Path(path).unlink(missing_ok=True)


# ── diff fidelity: id-less entities must not be silently dropped ───────────────


def test_compare_worlds_idless_entity_not_dropped(tmp_path):
    """An entity added without the chosen id key must still surface in the diff.

    Regression: when the representative element has an 'id', _diff_value keyed the
    whole list by 'id' and silently dropped any entity lacking that key — so adding
    an id-less NPC produced zero changes.
    """
    from iw_architect.tools.analysis import compare_worlds
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a))
    create_new_world_json(str(b))

    keyed_npc = {"id": "NPC000001", "name": "Bob", "positionInList": 0}
    world_a = json.loads(a.read_text())
    world_a["NPCs"] = [keyed_npc]
    a.write_text(json.dumps(world_a))

    world_b = json.loads(b.read_text())
    # Alice has a name but no 'id' — the old code dropped her from the keyed map.
    world_b["NPCs"] = [keyed_npc, {"name": "Alice", "positionInList": 1}]
    b.write_text(json.dumps(world_b))

    result = json.loads(compare_worlds(str(a), str(b)))
    assert result["total_changes"] > 0
    assert any("NPCs" in c["path"] for c in result["changes"])


def test_get_diff_summary_idless_entity_surfaced(tmp_path):
    """The narrative summary must report the id-less entity change too."""
    from iw_architect.tools.analysis import get_diff_summary
    from iw_architect.tools.helpers import create_new_world_json

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    create_new_world_json(str(a))
    create_new_world_json(str(b))

    keyed = {"id": "NPC000001", "name": "Bob", "positionInList": 0}
    world_a = json.loads(a.read_text())
    world_a["NPCs"] = [keyed]
    a.write_text(json.dumps(world_a))

    world_b = json.loads(b.read_text())
    world_b["NPCs"] = [keyed, {"name": "Alice", "positionInList": 1}]
    b.write_text(json.dumps(world_b))

    result = get_diff_summary(str(a), str(b))
    assert "No differences" not in result


def test_audit_per_character_overrides_present_ok(tmp_path):
    """When every per-character tracked item has an override, no finding fires.

    Locks the behavior of audit_world's per-character check ahead of refactoring.
    """
    from iw_architect.tools.analysis import audit_world

    world = _base()
    world["trackedItems"] = [
        {
            "id": "ITEM00001",
            "name": "Health",
            "positionInList": 0,
            "dataType": "number",
            "visibility": "everyone",
            "autoUpdate": False,
            "initialValueBasedOnPC": "character",
        }
    ]
    world["possibleCharacters"] = [
        {
            "name": "Alice",
            "characterId": "CHAR0001",
            "skills": {},
            "initialTrackedItemValues": [{"id": "ITEM00001", "value": "10"}],
        }
    ]
    path = _write(world)
    try:
        result = json.loads(audit_world(path))
        missing = [f for f in result["findings"] if f["type"] == "missing_per_character_overrides"]
        assert missing == []
    finally:
        Path(path).unlink(missing_ok=True)
