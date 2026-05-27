"""Two-tier world validator.

Tier 1: jsonschema structural validation (types, required fields, enum values).
Tier 2: custom semantic checks (cross-references, template variables, cross-field invariants).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

from iw_architect import KNOWN_SCHEMA_VERSION

_PLUGIN_ROOT = Path(__file__).parent.parent.parent  # src/iw_architect/ → src/ → repo root
_SCHEMA_PATH = _PLUGIN_ROOT / "references" / "world_v2.1.schema.json"
_SCHEMA: dict | None = None

_KNOWN_EFFECT_TYPES = {
    "effectShowMessage",
    "effectTellAIWhatToDo",
    "effectGiveInfo",
    "effectChangeBackground",
    "effectChangeMainInstructions",
    "effectChangeAuthorStyle",
    "effectChangeDescriptionInstructions",
    "effectChangeObjective",
    "effectChangeFirstAction",
    "effectChangePCName",
    "effectChangePCDescription",
    "effectChangePCSkill",
    "effectChangeVictoryCondition",
    "effectChangeDefeatCondition",
    "effectEndsGame",
    "effectModifyInstructionBlock",
    "effectModifyKeywordBlock",
    "effectSetTrackedItemValue",
    "effectModifyTrackedItemDetails",
    "effectPresentChoice",
    "effectRequestInput",
}

_KNOWN_CONDITION_TYPES = {
    "triggerOnCharacter",
    "triggerOnTrackedItem",
    "triggerOnRandomChance",
    "triggerOnTurn",
    "triggerOnEvent",
    "triggerBlockers",
    "triggerPrereqs",
}

# Variables always valid in template expressions
_ALWAYS_VALID_VARS = {"player_name", "turn_number", "random"}


def _get_schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(_SCHEMA_PATH.read_text())
    return _SCHEMA


def _snake(name: str) -> str:
    """Convert a display name to snake_case template variable name."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _collect_ids(world: dict) -> dict[str, set[str]]:
    """Collect all entity IDs from the world grouped by entity type."""
    ids: dict[str, set[str]] = {
        "character": set(),
        "npc": set(),
        "trackedItem": set(),
        "triggerEvent": set(),
        "instructionBlock": set(),
        "loreBookEntry": set(),
    }
    for ch in world.get("possibleCharacters", []):
        if cid := ch.get("characterId"):
            ids["character"].add(cid)
    for npc in world.get("NPCs", []):
        if nid := npc.get("id"):
            ids["npc"].add(nid)
    for ti in world.get("trackedItems", []):
        if tid := ti.get("id"):
            ids["trackedItem"].add(tid)
    for te in world.get("triggerEvents", []):
        if teid := te.get("id"):
            ids["triggerEvent"].add(teid)
    for ib in world.get("instructionBlocks", []):
        if iid := ib.get("id"):
            ids["instructionBlock"].add(iid)
    for lb in world.get("loreBookEntries", []):
        if lid := lb.get("id"):
            ids["loreBookEntry"].add(lid)
    return ids


def _skill_ids(world: dict) -> set[str]:
    """Return the set of valid skill_ template IDs derived from world skills."""
    return {f"skill_{_snake(s)}" for s in world.get("skills", [])}


def _check_schema_version(world: dict, errors: list[str], warnings: list[str]) -> None:
    version = world.get("schemaVersion")
    if version is None:
        return
    if not isinstance(version, (int, float)):
        return  # type mismatch already caught by Tier 1 jsonschema
    if version != KNOWN_SCHEMA_VERSION:
        if version > KNOWN_SCHEMA_VERSION:
            warnings.append(
                f"schemaVersion {version} is newer than the validator's known version "
                f"{KNOWN_SCHEMA_VERSION}. Some checks may not apply."
            )
        else:
            warnings.append(
                f"schemaVersion {version} is older than expected {KNOWN_SCHEMA_VERSION}."
            )


def _check_duplicate_ids(world: dict, errors: list[str], warnings: list[str]) -> None:
    def _check_array(entities: list[dict], id_field: str, label: str) -> None:
        seen: set = set()
        for entity in entities:
            eid = entity.get(id_field)
            if eid is not None:
                if eid in seen:
                    errors.append(f"Duplicate {id_field} '{eid}' in {label}")
                seen.add(eid)

    _check_array(world.get("possibleCharacters", []), "characterId", "possibleCharacters")
    _check_array(world.get("NPCs", []), "id", "NPCs")
    _check_array(world.get("trackedItems", []), "id", "trackedItems")
    _check_array(world.get("triggerEvents", []), "id", "triggerEvents")
    _check_array(world.get("instructionBlocks", []), "id", "instructionBlocks")
    _check_array(world.get("loreBookEntries", []), "id", "loreBookEntries")

    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        _check_array(trigger.get("triggerConditions", []), "id", f"trigger '{tname}' conditions")
        _check_array(trigger.get("triggerEffects", []), "id", f"trigger '{tname}' effects")


def _check_position_in_list(world: dict, errors: list[str], warnings: list[str]) -> None:
    def _check_array(entities: list[dict], label: str) -> None:
        positions = [e.get("positionInList") for e in entities if "positionInList" in e]
        if len(positions) != len(entities):
            missing = [i for i, e in enumerate(entities) if "positionInList" not in e]
            errors.append(f"{label}: {len(missing)} entities missing positionInList")
        dupes = [p for p in positions if positions.count(p) > 1]
        if dupes:
            errors.append(f"{label}: non-unique positionInList values: {sorted(set(dupes))}")

    _check_array(world.get("NPCs", []), "NPCs")
    _check_array(world.get("trackedItems", []), "trackedItems")


def _check_cross_field_invariants(world: dict, errors: list[str], warnings: list[str]) -> None:
    if world.get("nsfw") and not world.get("mature"):
        errors.append("nsfw: true requires mature: true")

    perms = world.get("permissionsOnceShared", {})
    if perms.get("editing") and not perms.get("sharing"):
        errors.append("permissionsOnceShared.editing: true requires sharing: true")

    for cond_name in ("victoryCondition", "defeatCondition"):
        cond = world.get(cond_name)
        if cond and isinstance(cond, dict) and cond.get("alreadyFired"):
            warnings.append(
                f"{cond_name}.alreadyFired is true — this is platform runtime state; "
                "do not set it to true in authored worlds."
            )


def _check_logic_conditions(world: dict, errors: list[str], warnings: list[str]) -> None:
    def _check_conditions(conditions: list[dict], trigger_name: str, advanced: bool) -> None:
        for cond in conditions:
            if cond.get("category") == "logic" and not advanced:
                errors.append(
                    f"Trigger '{trigger_name}': logic condition (id={cond.get('id')}) "
                    "requires advancedLogic: true on the trigger"
                )
            if cond.get("category") == "logic":
                sub = cond.get("data", [])
                if isinstance(sub, list):
                    _check_conditions(sub, trigger_name, advanced)

    for trigger in world.get("triggerEvents", []):
        advanced = trigger.get("advancedLogic", False)
        name = trigger.get("name", trigger.get("id", "?"))
        _check_conditions(trigger.get("triggerConditions", []), name, advanced)


def _resolve_tracked_item_ref(
    ref: str, tracked_item_ids: set[str], skill_ids: set[str]
) -> str | None:
    """Return error message if ref is invalid, else None."""
    if ref in tracked_item_ids:
        return None
    if ref in skill_ids:
        return None
    if ref.startswith("skill_"):
        return f"Tracked item reference '{ref}' not found (unknown skill)"
    return f"Tracked item ID '{ref}' not found"


def _check_cross_references(world: dict, errors: list[str], warnings: list[str]) -> None:
    ids = _collect_ids(world)
    valid_skill_ids = _skill_ids(world)

    def _check_cond_refs(conditions: list[dict], tname: str) -> None:
        for cond in conditions:
            cat = cond.get("category")
            ctype = cond.get("type")

            if cat == "condition":
                data = cond.get("data")
                if ctype == "triggerOnCharacter" and isinstance(data, list):
                    for cid in data:
                        if cid not in ids["character"]:
                            errors.append(
                                f"Trigger '{tname}': triggerOnCharacter references "
                                f"unknown characterId '{cid}'"
                            )
                elif ctype == "triggerOnTrackedItem" and isinstance(data, dict):
                    ref = data.get("trackedItemID") or cond.get("trackedItemID")
                    if ref:
                        err = _resolve_tracked_item_ref(ref, ids["trackedItem"], valid_skill_ids)
                        if err:
                            errors.append(f"Trigger '{tname}': {err}")
                elif ctype == "triggerPrereqs" and isinstance(data, list):
                    for prereq_id in data:
                        if prereq_id not in ids["triggerEvent"]:
                            errors.append(
                                f"Trigger '{tname}': triggerPrereqs references "
                                f"unknown trigger id '{prereq_id}'"
                            )
                elif ctype == "triggerBlockers" and isinstance(data, list):
                    for blocker_id in data:
                        if blocker_id not in ids["triggerEvent"]:
                            errors.append(
                                f"Trigger '{tname}': triggerBlockers references "
                                f"unknown trigger id '{blocker_id}'"
                            )

            elif cat == "logic":
                sub = cond.get("data", [])
                if isinstance(sub, list):
                    _check_cond_refs(sub, tname)

    # Validate trigger conditions and effects
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        _check_cond_refs(trigger.get("triggerConditions", []), tname)

        for effect in trigger.get("triggerEffects", []):
            etype = effect.get("type")
            data = effect.get("data")

            if etype == "effectModifyInstructionBlock" and isinstance(data, dict):
                block_id = data.get("id")
                if block_id and block_id not in ids["instructionBlock"]:
                    errors.append(
                        f"Trigger '{tname}': effectModifyInstructionBlock references "
                        f"unknown instructionBlock id '{block_id}'"
                    )
            elif etype == "effectModifyKeywordBlock" and isinstance(data, dict):
                block_id = data.get("id")
                if block_id and block_id not in ids["loreBookEntry"]:
                    errors.append(
                        f"Trigger '{tname}': effectModifyKeywordBlock references "
                        f"unknown loreBookEntry id '{block_id}'"
                    )
            elif etype in ("effectSetTrackedItemValue", "effectModifyTrackedItemDetails"):
                ref = (isinstance(data, dict) and data.get("trackedItemID")) or effect.get(
                    "trackedItemID"
                )
                if ref:
                    if ref not in ids["trackedItem"]:
                        errors.append(
                            f"Trigger '{tname}': {etype} references unknown trackedItem id '{ref}'"
                        )
            elif etype == "effectPresentChoice" and isinstance(data, dict):
                ref = data.get("targetTrackedItemId")
                if ref and ref not in ids["trackedItem"]:
                    errors.append(
                        f"Trigger '{tname}': effectPresentChoice references "
                        f"unknown trackedItem id '{ref}'"
                    )
            elif etype == "effectRequestInput" and isinstance(data, dict):
                ref = data.get("targetTrackedItemId")
                if ref and ref not in ids["trackedItem"]:
                    errors.append(
                        f"Trigger '{tname}': effectRequestInput references "
                        f"unknown trackedItem id '{ref}'"
                    )
            elif etype and etype not in _KNOWN_EFFECT_TYPES:
                warnings.append(
                    f"Trigger '{tname}': unknown effect type '{etype}' "
                    "(may be a future platform feature — preserved verbatim)"
                )

            # Warn on unknown condition types
        for cond in trigger.get("triggerConditions", []):
            ctype = cond.get("type")
            if (
                ctype
                and ctype not in _KNOWN_CONDITION_TYPES
                and cond.get("category") == "condition"
            ):
                warnings.append(
                    f"Trigger '{tname}': unknown condition type '{ctype}' "
                    "(may be a future platform feature — preserved verbatim)"
                )


def _extract_template_var_names(text: str) -> list[str]:
    """Extract simple identifier names from <<...>> template expressions."""
    results = []
    for match in re.finditer(r"<<([^>]+)>>", text):
        expr = match.group(1).strip()
        # Only validate simple identifiers (no operators/functions)
        if re.fullmatch(r"[a-z_][a-z0-9_]*", expr):
            results.append(expr)
    return results


def _check_template_variables(world: dict, errors: list[str], warnings: list[str]) -> None:
    tracked_item_vars = {_snake(ti["name"]) for ti in world.get("trackedItems", []) if "name" in ti}
    valid_skill_ids = _skill_ids(world)
    # initial_<varname> is valid for any numerical tracked item or skill
    valid_initial = {
        f"initial_{v}" for v in tracked_item_vars | {s[len("skill_") :] for s in valid_skill_ids}
    }

    valid_vars = _ALWAYS_VALID_VARS | tracked_item_vars | valid_skill_ids | valid_initial

    def _check_text(text: str, location: str) -> None:
        for var in _extract_template_var_names(text):
            if var not in valid_vars:
                warnings.append(
                    f"{location}: template variable '<<{var}>>' may not be declared "
                    "(no matching tracked item, skill, or built-in variable)"
                )

    def _check_dict_texts(obj: Any, location: str) -> None:
        if isinstance(obj, str):
            _check_text(obj, location)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check_dict_texts(v, f"{location}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_dict_texts(item, f"{location}[{i}]")

    # Check main text fields
    for field in (
        "background",
        "instructions",
        "authorStyle",
        "firstInput",
        "objective",
        "descriptionRequest",
        "evaluationRequest",
        "summaryRequest",
    ):
        if val := world.get(field):
            _check_text(val, field)

    for ti in world.get("trackedItems", []):
        name = ti.get("name", "?")
        for f in ("description", "updateInstructions"):
            if val := ti.get(f):
                _check_text(val, f"trackedItems[name={name}].{f}")

    for ib in world.get("instructionBlocks", []):
        if val := ib.get("content"):
            _check_text(val, f"instructionBlocks[name={ib.get('name', '?')}].content")

    for lb in world.get("loreBookEntries", []):
        if val := lb.get("content"):
            _check_text(val, f"loreBookEntries[name={lb.get('name', '?')}].content")


def _check_unknown_top_level_keys(world: dict, errors: list[str], warnings: list[str]) -> None:
    schema = _get_schema()
    known = set(schema.get("properties", {}).keys())
    for key in world:
        if key not in known:
            warnings.append(
                f"Unknown top-level key '{key}' — not in the known schema but preserved verbatim"
            )


def validate_world(world_path: str) -> str:
    """Strict schema check. Reports every error that would cause the platform to
    reject or misinterpret the world. Returns JSON with 'valid', 'errors', and 'warnings'.
    """
    path = Path(world_path)
    if not path.exists():
        return json.dumps(
            {"valid": False, "errors": [f"File not found: {world_path}"], "warnings": []}
        )

    try:
        world = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return json.dumps({"valid": False, "errors": [f"Invalid JSON: {exc}"], "warnings": []})

    errors: list[str] = []
    warnings: list[str] = []

    # Tier 1: jsonschema structural validation
    schema = _get_schema()
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(world), key=lambda e: list(e.path)):
        path_str = ".".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"[{path_str}] {error.message}")

    # Tier 2: semantic checks
    _check_schema_version(world, errors, warnings)
    _check_duplicate_ids(world, errors, warnings)
    _check_position_in_list(world, errors, warnings)
    _check_cross_field_invariants(world, errors, warnings)
    _check_logic_conditions(world, errors, warnings)
    _check_cross_references(world, errors, warnings)
    _check_template_variables(world, errors, warnings)
    _check_unknown_top_level_keys(world, errors, warnings)

    return json.dumps(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        },
        indent=2,
    )
