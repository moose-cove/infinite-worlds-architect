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
import yaml

from iw_architect import KNOWN_SCHEMA_VERSION
from iw_architect.paths import RelativePathError, require_absolute

_PLUGIN_ROOT = Path(__file__).parent.parent.parent  # src/iw_architect/ → src/ → repo root
_SCHEMA_PATH = _PLUGIN_ROOT / "references" / "world_v2.4.schema.json"
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
    # rec 4 (KB-empirical): historically schema-absent but confirmed working in real worlds.
    # Source: iw_knowledge_base_v2_8.md "Import Test Results".
    "effectFireRandomTrigger",
    # schema v2.2: PawScript. Runs a script that can only mutate tracked items.
    # Source: https://infiniteworlds.app/pawscript-script-guide
    "effectRunScript",
}

# rec 7: SoG = Start-of-Game (triggerOnStartOfGame: true on the trigger).
# SoG-only effects are silently ignored in regular triggers;
# regular-only effects are stripped in SoG.
# Source: iw_knowledge_base_v2_8.md "All Effect Types" table.
_SOG_ONLY_EFFECTS = {"effectChangeBackground", "effectChangeFirstAction"}
_REGULAR_ONLY_EFFECTS = {"effectGiveInfo", "effectFireRandomTrigger"}

# rec 3: required data keys for player-interaction effects.
# effectPresentChoice: all 8 keys must be present (even in single-select; min/max may be null).
# Source: fixture + WORLD_JSON_SCHEMA_v2.4.md.
_EFFECT_PRESENT_CHOICE_REQUIRED_KEYS = {
    "message",
    "choices",
    "selectionMode",
    "minSelections",
    "maxSelections",
    "updateMode",
    "valueDelimiter",
    "targetTrackedItemId",
}
# effectRequestInput: 4 required keys.
_EFFECT_REQUEST_INPUT_REQUIRED_KEYS = {
    "requestText",
    "targetTrackedItemId",
    "requiresInput",
    "inputMode",
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

# Condition trees are author-controlled and arbitrarily deep (`category: "logic"` nests
# recursively). Python's own recursion limit is the real ceiling, and blowing it raises
# RecursionError out of validate_world instead of returning a report. Depth beyond this is
# far past anything the editor can produce, so stopping the walk is strictly better than
# crashing — and validate_world wraps Tier 2 in a RecursionError guard as a second net.
_MAX_CONDITION_DEPTH = 100

# Documented cap on AI-evaluated events per world (references/fields/TRIGGER_EVENTS.md; the
# wiki says "only ten custom situation conditions can be created and used"). Wiki-corroborated
# rather than fixture-proven, so it drives a warning, never an error.
_MAX_AI_EVENT_CONDITIONS = 10


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
    # `entities` is annotated Any, not list[dict]: it comes straight from author-controlled
    # JSON, so the isinstance guards below are load-bearing runtime checks, not dead code.
    def _check_array(entities: Any, id_field: str, label: str) -> None:
        seen: set = set()
        if not isinstance(entities, list):
            return  # Tier 1 already reported the type error
        for entity in entities:
            # This runs before every other Tier 2 check, so a non-dict entry here would crash
            # the whole pass and make the downstream isinstance guards unreachable.
            if not isinstance(entity, dict):
                errors.append(f"{label}: entry is not an object ({type(entity).__name__})")
                continue
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
            # positionInList should be numeric (Tier 1 enforces the type), but a
            # malformed/hand-edited world can put anything here — including
            # unhashable (dict/list) or unorderable (None/mixed) values. Dedupe
            # with ``==`` (no hashing) and sort via a string key (no raw
            # comparison) so this report never crashes on the bad value that the
            # Tier 1 type error already flags.
            distinct: list = []
            for p in dupes:
                if p not in distinct:
                    distinct.append(p)
            try:
                rendered = sorted(distinct)
            except TypeError:
                rendered = sorted(distinct, key=lambda p: (p is None, type(p).__name__, str(p)))
            errors.append(f"{label}: non-unique positionInList values: {rendered}")

    _check_array(world.get("NPCs", []), "NPCs")
    _check_array(world.get("trackedItems", []), "trackedItems")


# Recommended default for imageStyle, the one image field the schema allows to be
# null. Null is tolerated but discouraged; this is the value the scaffold seeds and
# the warning recommends. The sibling image fields stay string-only — a null there
# is a Tier 1 error, and "" is the correct "unset" value.
_IMAGE_STYLE_DEFAULT = "photo_1"


def _check_tracked_item_id_charset(world: dict, errors: list[str], warnings: list[str]) -> None:
    """Warn when a tracked-item id contains non-alphanumeric characters.

    IW silently renames tracked-item IDs that contain non-alphanumeric characters (e.g. '+',
    '/', '-') on import, WITHOUT updating trigger references — confirmed via import test (June
    2026): 'trkPlus+1' was renamed to 'JOgXHlGyO' and 'trkSlsh/2' to 'Yi3bE076Q', leaving
    8 dangling trigger references. Other entity kinds (EIB, KIB, trigger-event) survived '+/'
    unchanged in the same test — so this warning is scoped to tracked items only.

    mint_ids now emits alphanumeric-only IDs. This warning catches IDs authored by hand or
    imported from older worlds.
    """
    _NON_ALNUM = re.compile(r"[^A-Za-z0-9]")
    for ti in world.get("trackedItems", []):
        tid = ti.get("id")
        if tid and _NON_ALNUM.search(tid):
            name = ti.get("name", "?")
            warnings.append(
                f"trackedItems[name={name!r}]: id {tid!r} contains non-alphanumeric characters. "
                "IW silently renames such tracked-item IDs on import WITHOUT updating trigger "
                "references, leaving dangling refs and broken triggers (confirmed import test, "
                "June 2026). Use alphanumeric-only IDs (A-Za-z0-9)."
            )


def _check_null_image_fields(world: dict, errors: list[str], warnings: list[str]) -> None:
    """Warn when imageStyle is explicitly null.

    The schema permits null for imageStyle (pass-through tolerance) but it is not
    recommended — prefer a style preset such as "photo_1". The sibling image fields
    are string-only; null there is caught as a Tier 1 error, not warned here.
    """
    if world.get("imageStyle", "") is None:
        warnings.append(
            f"imageStyle is null — not recommended; set a style preset "
            f"(plugin default: {_IMAGE_STYLE_DEFAULT!r})"
        )


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


def _check_tracked_item_condition_data(world: dict, errors: list[str], warnings: list[str]) -> None:
    """rec 1 + rec 2: validate triggerOnTrackedItem condition data fields.

    rec 1 (WARNING): empty-string inequality or textComparison is silently stripped by IW on import.
    rec 2 (ERROR): non-string requiredValue causes AttributeError crash on IW import
        (IW calls .strip() on it → 'int' object has no attribute 'strip').
    Source: iw_knowledge_base_v2_8.md "triggerOnTrackedItem — Definitive Correct Format".
    """
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        for cond in trigger.get("triggerConditions", []):
            if cond.get("type") != "triggerOnTrackedItem":
                continue
            data = cond.get("data")
            if not isinstance(data, dict):
                continue
            cond_id = cond.get("id", "?")

            # rec 1: empty-string inequality or textComparison is silently stripped on import
            if data.get("inequality") == "":
                warnings.append(
                    f"Trigger '{tname}' condition '{cond_id}': triggerOnTrackedItem "
                    "data.inequality is empty string — silently stripped on IW import"
                )
            if data.get("textComparison") == "":
                warnings.append(
                    f"Trigger '{tname}' condition '{cond_id}': triggerOnTrackedItem "
                    "data.textComparison is empty string — silently stripped on IW import"
                )

            # rec 2: non-string requiredValue causes an AttributeError crash on IW import
            rv = data.get("requiredValue")
            if rv is not None and not isinstance(rv, str):
                errors.append(
                    f"Trigger '{tname}' condition '{cond_id}': triggerOnTrackedItem "
                    f"data.requiredValue must be a string (got {type(rv).__name__}) — "
                    "IW crashes on import with AttributeError: object has no attribute 'strip'"
                )


def _check_player_interaction_effect_shapes(
    world: dict, errors: list[str], warnings: list[str]
) -> None:
    """rec 3: validate effectPresentChoice and effectRequestInput data shapes.

    Both effects are silently stripped if their data is malformed.
    All required keys must be present (minSelections/maxSelections may be null).
    Source: fixture + WORLD_JSON_SCHEMA_v2.4.md + iw_knowledge_base_v2_8.md.
    """
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        for effect in trigger.get("triggerEffects", []):
            etype = effect.get("type")
            data = effect.get("data")
            eid = effect.get("id", "?")

            # A non-dict `data` is itself malformed (IW silently strips it), so warn
            # for that case too — not only for a dict missing required keys.
            if etype == "effectPresentChoice":
                if not isinstance(data, dict):
                    warnings.append(
                        f"Trigger '{tname}' effect '{eid}': effectPresentChoice "
                        f"data is not a dict (got {type(data).__name__}) — "
                        "silently stripped on IW import if malformed"
                    )
                else:
                    missing = _EFFECT_PRESENT_CHOICE_REQUIRED_KEYS - set(data.keys())
                    if missing:
                        warnings.append(
                            f"Trigger '{tname}' effect '{eid}': effectPresentChoice "
                            f"data missing required keys {sorted(missing)} — "
                            "silently stripped on IW import if malformed"
                        )

            elif etype == "effectRequestInput":
                if not isinstance(data, dict):
                    warnings.append(
                        f"Trigger '{tname}' effect '{eid}': effectRequestInput "
                        f"data is not a dict (got {type(data).__name__}) — "
                        "silently stripped on IW import if malformed"
                    )
                else:
                    missing = _EFFECT_REQUEST_INPUT_REQUIRED_KEYS - set(data.keys())
                    if missing:
                        warnings.append(
                            f"Trigger '{tname}' effect '{eid}': effectRequestInput "
                            f"data missing required keys {sorted(missing)} — "
                            "silently stripped on IW import if malformed"
                        )


def _check_set_tracked_item_value_shapes(
    world: dict, errors: list[str], warnings: list[str]
) -> None:
    """rec 9 (validator slice): effectSetTrackedItemValue data must include 'replaceWith'.

    KB-empirical import requirement: replaceWith must be present for all actions
    (use "" when unused); it is only *consumed* by the 'replace' action.
    Source: iw_knowledge_base_v2_8.md "Verified Corrections".
    """
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        for effect in trigger.get("triggerEffects", []):
            if effect.get("type") != "effectSetTrackedItemValue":
                continue
            data = effect.get("data")
            eid = effect.get("id", "?")
            if isinstance(data, dict) and "replaceWith" not in data:
                warnings.append(
                    f"Trigger '{tname}' effect '{eid}': effectSetTrackedItemValue data "
                    "is missing 'replaceWith' key — must be present for all actions "
                    '(use "" when unused); KB-empirical import requirement '
                    "(iw_knowledge_base_v2_8.md 'Verified Corrections')"
                )


def _check_sog_effect_context(world: dict, errors: list[str], warnings: list[str]) -> None:
    """rec 7: warn when SoG-only effects appear in regular triggers, or vice versa.

    SoG trigger = triggerOnStartOfGame: true on the trigger object.
    SoG-only effects (effectChangeBackground, effectChangeFirstAction) are silently
    ignored in regular (non-SoG) triggers.
    Regular-only effects (effectGiveInfo, effectFireRandomTrigger) are silently stripped
    in SoG triggers.
    Source: iw_knowledge_base_v2_8.md "All Effect Types" table + fixture verification.
    """
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        # identity check (`is True`): only literal True counts, not truthy 1/"true".
        # Do not "simplify" to bool(...) — a non-bool value here is itself a Tier 1 type
        # error, and treating it as truthy would mask that and emit a misleading SoG warning.
        is_sog = trigger.get("triggerOnStartOfGame", False) is True

        for effect in trigger.get("triggerEffects", []):
            etype = effect.get("type")
            if not etype:
                continue
            eid = effect.get("id", "?")

            if is_sog and etype in _REGULAR_ONLY_EFFECTS:
                warnings.append(
                    f"Trigger '{tname}' effect '{eid}': {etype} is silently stripped "
                    "in Start-of-Game triggers — it only works in regular (non-SoG) triggers"
                )
            elif not is_sog and etype in _SOG_ONLY_EFFECTS:
                warnings.append(
                    f"Trigger '{tname}' effect '{eid}': {etype} is Start-of-Game-only — "
                    "silently ignored in regular triggers "
                    "(KB-empirical; iw_knowledge_base_v2_8.md 'All Effect Types')"
                )


def _check_skills_not_empty(world: dict, errors: list[str], warnings: list[str]) -> None:
    """rec 6: warn when the top-level skills array is empty.

    KB v2.8 asserts an empty skills array breaks import; not live-verified here —
    warning only (not an error). Note: this is the world-level skills string array,
    NOT the per-character skills object map (a different field entirely).
    Source: iw_knowledge_base_v2_8.md.
    """
    skills = world.get("skills")
    if isinstance(skills, list) and len(skills) == 0:
        # hideSkillSystem: true might legitimately suppress skills — note the caveat
        hide = world.get("hideSkillSystem", False)
        if hide:
            warnings.append(
                "skills is empty and hideSkillSystem is true — if this world uses skill-based "
                "triggers or tracking, a non-empty skills array may be required on IW import "
                "(KB-empirical; iw_knowledge_base_v2_8.md)"
            )
        else:
            warnings.append(
                "skills is empty — KB v2.8 asserts an empty skills array may break IW import; "
                "seed at least one skill string (e.g. 'General') "
                "(KB-empirical; iw_knowledge_base_v2_8.md)"
            )


# ── schema v2.2: PawScript + YAML tracked items ──────────────────────────────
#
# PawScript scripts (effectRunScript.data) can only mutate tracked items, referenced
# as $<variableName>. The natives $player and $game are read-only. See
# https://infiniteworlds.app/pawscript-script-guide and
# https://infiniteworlds.app/pawscript-reference.

_VARIABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Read-only PawScript natives — writing to them is rejected at runtime.
_SCRIPT_NATIVES = {"player", "game"}
# A `$root` reference (root = text before any `.`), e.g. $puppy.friendliness → "puppy".
_SCRIPT_IDENT_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
# `for each $x in ...` introduces $x as a locally-bound (and assignable) loop variable.
_SCRIPT_LOOP_RE = re.compile(r"^\s*for\s+each\s+\$([A-Za-z_][A-Za-z0-9_]*)\s+in\b")
# `set $x = ...` introduces $x as a locally-bound scratch (working) variable.
_SCRIPT_SET_RE = re.compile(r"^\s*set\s+\$([A-Za-z_][A-Za-z0-9_]*)\b")
# An assignment statement: `$root(.field)* <op>= ...`. The `(?!=)` guard keeps `==`
# (a comparison) from being read as an assignment.
_SCRIPT_ASSIGN_RE = re.compile(
    r"^\s*\$([A-Za-z_][A-Za-z0-9_]*)(?:\.[A-Za-z0-9_.]*)?\s*[+\-*/%]?=(?!=)"
)


def _collect_variable_names(world: dict) -> list[str]:
    """Return the tracked items' non-empty string ``variableName`` values (schema v2.2)."""
    names: list[str] = []
    for ti in world.get("trackedItems", []):
        vn = ti.get("variableName")
        if isinstance(vn, str) and vn:
            names.append(vn)
    return names


def _check_tracked_item_variable_names(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.2: warn on malformed or duplicated tracked-item ``variableName`` values.

    variableName is the PawScript handle ($<variableName>); it must be a snake_case
    identifier and unique across tracked items or script references become ambiguous.
    """
    seen: dict[str, int] = {}
    for ti in world.get("trackedItems", []):
        vn = ti.get("variableName")
        if not isinstance(vn, str) or vn == "":
            continue
        name = ti.get("name", "?")
        if not _VARIABLE_NAME_RE.match(vn):
            warnings.append(
                f"trackedItems[name={name!r}]: variableName {vn!r} does not match "
                r"^[a-z][a-z0-9_]*$ — PawScript $<variableName> references may not resolve"
            )
        seen[vn] = seen.get(vn, 0) + 1
    for vn, count in sorted(seen.items()):
        if count > 1:
            warnings.append(
                f"Duplicate tracked-item variableName {vn!r} ({count} items) — "
                "PawScript $<variableName> references are ambiguous"
            )


def _strip_script_comments(script: str) -> list[str]:
    """Return the script's lines with ``#`` comment lines removed."""
    return [ln for ln in script.splitlines() if not ln.lstrip().startswith("#")]


def _check_pawscript_scripts(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.2: validate effectRunScript PawScript bodies.

    - Warn on a ``$root`` that is neither a tracked-item variableName, a native
      ($player/$game), a ``for each`` loop variable, nor a ``set`` scratch
      variable (an undeclared reference).
    - Warn on an assignment (including via ``set``) whose target root is a native
      ($player/$game are read-only and must not be reused as a set variable).

    Comment (``#``) lines are stripped first so URLs and prose never contribute
    spurious identifiers.

    This is a heuristic linter, not a PawScript parser. Two known limitations,
    both benign for a warn-only check: it has no string-literal awareness (a
    ``$name`` inside a quoted string is treated like a real reference), and it
    does not enforce declaration order (a ``$x`` used before its ``set`` /
    ``for each`` appears later in the script is still accepted, because loop and
    set variables are collected from the whole body first).
    """
    variable_names = set(_collect_variable_names(world))
    for trigger in world.get("triggerEvents", []):
        tname = trigger.get("name", trigger.get("id", "?"))
        for effect in trigger.get("triggerEffects", []):
            if effect.get("type") != "effectRunScript":
                continue
            script = effect.get("data")
            eid = effect.get("id", "?")
            if not isinstance(script, str):
                continue
            lines = _strip_script_comments(script)

            # Bind locally-introduced variables (locally legal roots): `for each $x in ...`
            # loop variables and `set $x = ...` scratch variables. A `set` that
            # targets a native name is flagged rather than bound — reusing the
            # reserved read-only $player/$game as a scratch variable is an author
            # error (whether it shadows or attempts to write the native).
            local_vars: set[str] = set()
            for ln in lines:
                m = _SCRIPT_LOOP_RE.match(ln)
                if m:
                    local_vars.add(m.group(1))
                sm = _SCRIPT_SET_RE.match(ln)
                if sm:
                    if sm.group(1) in _SCRIPT_NATIVES:
                        warnings.append(
                            f"Trigger '{tname}' effect '{eid}': effectRunScript uses "
                            f"'set ${sm.group(1)}' — $player and $game are reserved read-only "
                            "natives and must not be reused as a set variable"
                        )
                    else:
                        local_vars.add(sm.group(1))
            legal = variable_names | _SCRIPT_NATIVES | local_vars

            seen_unknown: set[str] = set()
            for ln in lines:
                for root in _SCRIPT_IDENT_RE.findall(ln):
                    if root not in legal and root not in seen_unknown:
                        seen_unknown.add(root)
                        warnings.append(
                            f"Trigger '{tname}' effect '{eid}': effectRunScript references "
                            f"${root} which is not a tracked-item variableName, a native "
                            "($player/$game), a for-each loop variable, or a set variable"
                        )
                am = _SCRIPT_ASSIGN_RE.match(ln)
                if am and am.group(1) in _SCRIPT_NATIVES:
                    warnings.append(
                        f"Trigger '{tname}' effect '{eid}': effectRunScript assigns to "
                        f"${am.group(1)} — the natives $player and $game are read-only at runtime"
                    )


def _check_enforce_format(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.2: warn when enforceFormat is true but formatSchema is empty/missing."""
    for ti in world.get("trackedItems", []):
        if ti.get("enforceFormat") is not True:
            continue
        fs = ti.get("formatSchema")
        if not (isinstance(fs, str) and fs.strip()):
            name = ti.get("name", "?")
            warnings.append(
                f"trackedItems[name={name!r}]: enforceFormat is true but formatSchema is "
                "empty — there is nothing to enforce; provide a formatSchema or set "
                "enforceFormat false"
            )


def _check_yaml_tracked_items(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.2: dataType 'yaml' items whose non-empty initialValue or formatExample
    fails to parse as YAML → error (the platform stores these as parseable YAML)."""
    for ti in world.get("trackedItems", []):
        if ti.get("dataType") != "yaml":
            continue
        name = ti.get("name", "?")
        for field in ("initialValue", "formatExample"):
            val = ti.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    yaml.safe_load(val)
                except (yaml.YAMLError, RecursionError) as exc:
                    # RecursionError: PyYAML is not depth-limited even under
                    # safe_load, so pathologically-nested author-controlled input
                    # would otherwise crash the whole validator instead of being
                    # reported here as an invalid-YAML error.
                    detail = str(exc).replace("\n", " ")
                    errors.append(
                        f"trackedItems[name={name!r}]: {field} is not valid YAML "
                        f"(dataType 'yaml'): {detail}"
                    )


def _check_xml_deprecation(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.2: dataType 'xml' is deprecated in favor of 'yaml'. Warning, never error."""
    for ti in world.get("trackedItems", []):
        if ti.get("dataType") == "xml":
            name = ti.get("name", "?")
            warnings.append(
                f"trackedItems[name={name!r}]: dataType 'xml' is deprecated (schema v2.2) — "
                "prefer 'yaml' for structured tracked-item data"
            )


def _check_event_conditions_registered(world: dict, errors: list[str], warnings: list[str]) -> None:
    """schema v2.4: keep a triggerOnEvent's event text in sync with the top-level
    `conditions` registry.

    Warning, never error. The fixture pairs one `conditions` entry with one `triggerOnEvent`
    whose `data` matches it byte-for-byte, and there is no ID or index linking the two, so
    exact text is the only available key. What the registry *does* is an open question: it may
    drive selectability in the editor's trigger UI, or it may be a platform-maintained index of
    the events already in use (which would also explain how the documented world-level cap of
    ten AI-evaluated events is enforced). The sync guidance is identical under either reading,
    so that is all this check asserts.

    Matching is exact after `strip()`. Case, internal whitespace and trailing punctuation are
    all significant — no normalization is applied, because the platform's own matching rule is
    undocumented and guessing at one would trade false negatives for false positives.

    Pre-v2.4 worlds have no `conditions` array at all and surface one warning per
    triggerOnEvent, which is the intended nudge on migration.
    """
    # `.get(key, default)` only defaults when the key is ABSENT. A world carrying an explicit
    # `"conditions": null` (or any non-list) would otherwise blow up here with a TypeError that
    # escapes validate_world entirely, breaking its documented "always returns a report"
    # contract. Tier 1 already reports the type error; Tier 2 just has to not crash on it.
    raw_conditions = world.get("conditions")
    declared = (
        {c.strip() for c in raw_conditions if isinstance(c, str)}
        if isinstance(raw_conditions, list)
        else set()
    )
    used: set[str] = set()

    def _walk(conditions: Any, tname: str, depth: int = 0) -> None:
        if depth > _MAX_CONDITION_DEPTH or not isinstance(conditions, list):
            return
        for cond in conditions:
            if not isinstance(cond, dict):
                continue
            if cond.get("category") == "logic":
                _walk(cond.get("data", []), tname, depth + 1)
                continue
            if cond.get("type") != "triggerOnEvent":
                continue
            event = cond.get("data")
            if not isinstance(event, str) or not event.strip():
                continue
            used.add(event.strip())
            if event.strip() not in declared:
                warnings.append(
                    f"Trigger '{tname}': triggerOnEvent event {event.strip()!r} is not "
                    "declared in the world's top-level 'conditions' registry (schema v2.4). "
                    "Add it verbatim — matching is by exact text."
                )

    for trigger in world.get("triggerEvents", []):
        _walk(
            trigger.get("triggerConditions", []),
            trigger.get("name", trigger.get("id", "?")),
        )

    for orphan in sorted(declared - used):
        warnings.append(
            f"conditions: declared event {orphan!r} is not used by any triggerOnEvent "
            "condition (schema v2.4)"
        )

    # The 10-event cap is documented in references/fields/TRIGGER_EVENTS.md and corroborated by
    # the wiki ("only ten custom situation conditions can be created and used"). Wiki-sourced,
    # so warn rather than error, and don't encode it as `maxItems` in the schema.
    event_count = max(len(declared), len(used))
    if event_count > _MAX_AI_EVENT_CONDITIONS:
        warnings.append(
            f"This world has {event_count} AI-evaluated events (triggerOnEvent / 'conditions' "
            f"entries); the platform's documented cap is {_MAX_AI_EVENT_CONDITIONS}. Each one "
            "costs an extra AI evaluation per turn, and events beyond the cap may be ignored."
        )


# schema v2.4 changed the `data` shape of the two trigger-gating condition types.
#   v2.2 and earlier: ["triggerId", ...]
#   v2.4:             {"<key>": ["triggerId", ...], "firedThisTurn": bool}
# The wrapper key is named after the condition. `firedThisTurn` is type-checked but its
# semantics are an open question — the fixture only ever shows false, and the plugin does
# not assume what true does (see references/WORLD_JSON_SCHEMA_v2.4.md). The legacy bare array
# is still accepted on read because worlds authored before v2.4 carry it and must keep
# validating; whether the PLATFORM migrates it on import is unverified, so the warning tells
# authors to migrate rather than blessing the old shape. New authoring emits the object form.
_GATE_CONDITION_DATA_KEYS = {
    "triggerPrereqs": "prereqs",
    "triggerBlockers": "blockers",
}


def _gate_condition_trigger_ids(
    ctype: str,
    data: Any,
    tname: str,
    errors: list[str],
    warnings: list[str],
) -> list[str]:
    """Validate a triggerPrereqs/triggerBlockers `data` payload, returning its trigger IDs.

    Accepts both the v2.4 object form and the pre-v2.4 bare array (with a warning), so a
    shape change never silently disables the dangling-reference check that follows.
    """
    key = _GATE_CONDITION_DATA_KEYS[ctype]

    if isinstance(data, list):
        warnings.append(
            f"Trigger '{tname}': {ctype} data uses the pre-v2.4 bare-array form. "
            f'schema v2.4 expects {{"{key}": [...], "firedThisTurn": false}}. Whether the '
            "platform migrates the legacy form on import is unverified — migrate it while "
            "you are in this world, and emit the object form for new conditions."
        )
        return [i for i in data if isinstance(i, str)]

    if not isinstance(data, dict):
        errors.append(
            f"Trigger '{tname}': {ctype} data must be an object with '{key}' "
            "(a list of trigger IDs) and 'firedThisTurn' (a boolean)"
        )
        return []

    inner = data.get(key)
    if not isinstance(inner, list):
        errors.append(f"Trigger '{tname}': {ctype} data is missing the '{key}' list of trigger IDs")
        inner = []
    if not isinstance(data.get("firedThisTurn"), bool):
        warnings.append(
            f"Trigger '{tname}': {ctype} data has no boolean 'firedThisTurn'; schema v2.4 "
            "expects one. Emit false — the only value the canonical fixture shows"
        )
    return [i for i in inner if isinstance(i, str)]


def _check_cross_references(world: dict, errors: list[str], warnings: list[str]) -> None:
    ids = _collect_ids(world)
    valid_skill_ids = _skill_ids(world)

    # `conditions` is Any, not list[dict]: author-controlled JSON, so the guards are runtime
    # checks rather than dead code.
    def _check_cond_refs(conditions: Any, tname: str, depth: int = 0) -> None:
        if depth > _MAX_CONDITION_DEPTH or not isinstance(conditions, list):
            return
        for cond in conditions:
            if not isinstance(cond, dict):
                continue
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
                elif ctype in _GATE_CONDITION_DATA_KEYS:
                    gate_ids = _gate_condition_trigger_ids(ctype, data, tname, errors, warnings)
                    for gate_id in gate_ids:
                        if gate_id not in ids["triggerEvent"]:
                            errors.append(
                                f"Trigger '{tname}': {ctype} references "
                                f"unknown trigger id '{gate_id}'"
                            )

            elif cat == "logic":
                sub = cond.get("data", [])
                if isinstance(sub, list):
                    _check_cond_refs(sub, tname, depth + 1)

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
    try:
        path = require_absolute(world_path)
    except RelativePathError as exc:
        return json.dumps({"valid": False, "errors": [str(exc)], "warnings": []})
    if not path.exists():
        return json.dumps(
            {"valid": False, "errors": [f"File not found: {world_path}"], "warnings": []}
        )

    try:
        world = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return json.dumps({"valid": False, "errors": [f"Invalid JSON: {exc}"], "warnings": []})
    except RecursionError:
        # CPython's JSON scanner recurses per nesting level, so a pathologically nested
        # world exhausts the stack before any check runs. Report it rather than propagating.
        return json.dumps(
            {
                "valid": False,
                "errors": ["Invalid JSON: nesting is too deep to parse"],
                "warnings": [],
            }
        )

    if not isinstance(world, dict):
        return json.dumps(
            {
                "valid": False,
                "errors": [f"World must be a JSON object, got {type(world).__name__}"],
                "warnings": [],
            }
        )

    errors: list[str] = []
    warnings: list[str] = []

    # Tier 1: jsonschema structural validation
    schema = _get_schema()
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(world), key=lambda e: list(e.path)):
        path_str = ".".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"[{path_str}] {error.message}")

    # Tier 2: semantic checks.
    #
    # Wrapped as a unit: every check below walks author-controlled structure, several of them
    # recursively, and this function's contract is that it ALWAYS returns a report. A malformed
    # world must never surface to an MCP caller as a raw traceback. Individual checks guard
    # their own inputs (see _MAX_CONDITION_DEPTH and the isinstance gates); this is the net
    # under those, so a gap in one of them degrades to a reported error instead of a crash.
    try:
        _check_schema_version(world, errors, warnings)
        _check_duplicate_ids(world, errors, warnings)
        _check_position_in_list(world, errors, warnings)
        _check_tracked_item_id_charset(world, errors, warnings)
        _check_null_image_fields(world, errors, warnings)
        _check_cross_field_invariants(world, errors, warnings)
        _check_logic_conditions(world, errors, warnings)
        _check_cross_references(world, errors, warnings)
        _check_template_variables(world, errors, warnings)
        _check_unknown_top_level_keys(world, errors, warnings)
        # KB v2.8 checks (recs 1, 2, 3, 6, 7, 9-validator)
        _check_tracked_item_condition_data(world, errors, warnings)
        _check_player_interaction_effect_shapes(world, errors, warnings)
        _check_set_tracked_item_value_shapes(world, errors, warnings)
        _check_sog_effect_context(world, errors, warnings)
        _check_skills_not_empty(world, errors, warnings)
        # schema v2.2: PawScript + YAML tracked items
        _check_tracked_item_variable_names(world, errors, warnings)
        _check_pawscript_scripts(world, errors, warnings)
        _check_enforce_format(world, errors, warnings)
        _check_yaml_tracked_items(world, errors, warnings)
        _check_xml_deprecation(world, errors, warnings)
        # schema v2.4: named-event registry
        _check_event_conditions_registered(world, errors, warnings)
    except RecursionError:
        errors.append(
            "Semantic validation stopped: the world's structure is nested too deeply to "
            "analyze. Tier 1 (structural) results above are complete; Tier 2 checks are not."
        )
    except (TypeError, AttributeError, ValueError, KeyError) as exc:
        # Defensive: a shape no check anticipated. Surfacing it as an error keeps the tool
        # contract intact and still tells the author their world is malformed.
        errors.append(
            f"Semantic validation stopped on malformed world data: {type(exc).__name__}: {exc}"
        )

    return json.dumps(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        },
        indent=2,
    )
