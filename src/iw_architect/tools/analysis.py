"""Analysis tools: audit_world, compare_worlds, get_diff_summary."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from iw_architect.paths import require_absolute


def _load_world(world_path: str) -> dict:
    path = require_absolute(world_path)
    if not path.exists():
        raise FileNotFoundError(f"World file not found: {world_path}")
    return json.loads(path.read_text())


def _token_estimate(text: str) -> int:
    """Rough token count: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def _text_budget(world: dict) -> dict[str, int]:
    """Estimate token usage by section."""
    budgets: dict[str, int] = {}

    def _add(key: str, text: Any) -> None:
        if isinstance(text, str):
            budgets[key] = budgets.get(key, 0) + _token_estimate(text)
        elif isinstance(text, list):
            for item in text:
                if isinstance(item, str):
                    budgets[key] = budgets.get(key, 0) + _token_estimate(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            budgets[key] = budgets.get(key, 0) + _token_estimate(v)

    for field in ("background", "instructions", "authorStyle", "firstInput", "objective"):
        _add(field, world.get(field, ""))

    npc_total = sum(
        _token_estimate(str(npc.get("detail", ""))) + _token_estimate(str(npc.get("one_liner", "")))
        for npc in world.get("NPCs", [])
    )
    if npc_total:
        budgets["NPCs"] = npc_total

    ti_total = sum(
        _token_estimate(str(ti.get("description", "")))
        + _token_estimate(str(ti.get("updateInstructions", "")))
        for ti in world.get("trackedItems", [])
    )
    if ti_total:
        budgets["trackedItems"] = ti_total

    ib_total = sum(
        _token_estimate(str(ib.get("content", ""))) for ib in world.get("instructionBlocks", [])
    )
    if ib_total:
        budgets["instructionBlocks"] = ib_total

    lb_total = sum(
        _token_estimate(str(lb.get("content", ""))) for lb in world.get("loreBookEntries", [])
    )
    if lb_total:
        budgets["loreBookEntries"] = lb_total

    trigger_total = sum(
        _token_estimate(str(eff.get("data", "")))
        for te in world.get("triggerEvents", [])
        for eff in te.get("triggerEffects", [])
        if isinstance(eff.get("data"), str)
    )
    if trigger_total:
        budgets["triggerEffects"] = trigger_total

    return budgets


def _build_prereq_graph(world: dict) -> dict[str, list[str]]:
    """Build trigger-ID → list of prerequisite trigger-IDs graph."""
    graph: dict[str, list[str]] = {}
    for te in world.get("triggerEvents", []):
        tid = te.get("id")
        if not tid:
            continue
        prereqs: list[str] = []
        for cond in te.get("triggerConditions", []):
            if cond.get("type") == "triggerPrereqs" and isinstance(cond.get("data"), list):
                prereqs.extend(cond["data"])
        graph[tid] = prereqs
    return graph


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DFS cycle detection. Returns list of cycles (each as a list of node IDs)."""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in in_stack:
                # Found a back edge — record cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        path.pop()
        in_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def _menu_backed_items(world: dict) -> dict[str, dict]:
    """Map tracked-item id → {name, options} for items whose per-character
    ``initialPCValue`` is an array (a pick-one selection menu).

    When ``initialPCValue`` is a string array the player picks exactly one
    option at character selection, and that single choice becomes the item's
    active value — the item never holds every option at once. Options are
    unioned across all characters that offer a menu for the item.
    """
    menu: dict[str, dict] = {}
    for ch in world.get("possibleCharacters", []):
        for itv in ch.get("initialTrackedItemValues", []):
            value = itv.get("initialPCValue")
            if not isinstance(value, list):
                continue
            tid = itv.get("id")
            if not tid:
                continue
            entry = menu.setdefault(tid, {"name": itv.get("name", tid), "options": []})
            for opt in value:
                if isinstance(opt, str) and opt not in entry["options"]:
                    entry["options"].append(opt)
    return menu


def _iter_leaf_conditions(conditions: Any) -> Iterator[dict]:
    """Yield leaf trigger conditions, descending into compound logic groups.

    A compound condition has ``category == "logic"`` and a list ``data`` of
    sub-conditions; leaves carry a ``type`` (e.g. ``triggerOnTrackedItem``).
    """
    if not isinstance(conditions, list):
        return
    for cond in conditions:
        if not isinstance(cond, dict):
            continue
        if cond.get("category") == "logic" and isinstance(cond.get("data"), list):
            yield from _iter_leaf_conditions(cond["data"])
        else:
            yield cond


def audit_world(world_path: str) -> str:
    """Quality and optimization analysis: token budgets, trigger-graph cycles, redundancy.

    Returns JSON with findings (not pass/fail).
    """
    try:
        world = _load_world(world_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return json.dumps({"error": str(exc)})

    findings: list[dict] = []

    # Token budgets
    budgets = _text_budget(world)
    total_tokens = sum(budgets.values())
    findings.append(
        {
            "type": "token_budget",
            "severity": "info",
            "summary": f"Estimated total context tokens: ~{total_tokens}",
            "detail": {k: f"~{v}" for k, v in sorted(budgets.items(), key=lambda x: -x[1])},
        }
    )

    heavy = {k: v for k, v in budgets.items() if v > 1000}
    if heavy:
        findings.append(
            {
                "type": "token_budget_warning",
                "severity": "warning",
                "summary": "Some sections use >1000 estimated tokens",
                "detail": {k: f"~{v}" for k, v in heavy.items()},
                "suggestion": "Consider condensing these sections to reduce AI context cost.",
            }
        )

    # Trigger-graph cycle detection
    graph = _build_prereq_graph(world)
    cycles = _find_cycles(graph)
    if cycles:
        trigger_names = {
            te.get("id"): te.get("name", te.get("id")) for te in world.get("triggerEvents", [])
        }
        for cycle in cycles:
            named = [trigger_names.get(nid, nid) for nid in cycle]
            findings.append(
                {
                    "type": "trigger_cycle",
                    "severity": "error",
                    "summary": "Trigger prerequisite cycle detected",
                    "cycle": named,
                    "suggestion": "Break the cycle by removing one triggerPrereqs condition.",
                }
            )
    else:
        findings.append(
            {
                "type": "trigger_graph",
                "severity": "ok",
                "summary": "No prerequisite cycles detected in trigger graph",
            }
        )

    # Redundancy: NPC names mentioned verbatim in instructions
    instructions = world.get("instructions", "")
    npc_names_in_instructions = []
    for npc in world.get("NPCs", []):
        name = npc.get("name", "")
        if name and name in instructions:
            npc_names_in_instructions.append(name)
    if npc_names_in_instructions:
        findings.append(
            {
                "type": "npc_instruction_overlap",
                "severity": "info",
                "summary": "NPC names found in main instructions",
                "npcs": npc_names_in_instructions,
                "suggestion": (
                    "The platform automatically provides NPC details to the AI. "
                    "Brief mentions in instructions are fine, but full NPC "
                    "descriptions in instructions are redundant and waste tokens."
                ),
            }
        )

    # Instruction blocks with very short content
    short_blocks = [
        ib.get("name", "?")
        for ib in world.get("instructionBlocks", [])
        if len(ib.get("content", "")) < 10
    ]
    if short_blocks:
        findings.append(
            {
                "type": "empty_instruction_blocks",
                "severity": "warning",
                "summary": "Instruction blocks with very short content",
                "blocks": short_blocks,
                "suggestion": "Consider adding meaningful content or removing empty blocks.",
            }
        )

    # Triggers without any conditions (always fires unless triggerOnStartOfGame)
    unconditioned = []
    for te in world.get("triggerEvents", []):
        conds = te.get("triggerConditions", [])
        if not conds and not te.get("triggerOnStartOfGame"):
            unconditioned.append(te.get("name", te.get("id", "?")))
    if unconditioned:
        findings.append(
            {
                "type": "unconditioned_triggers",
                "severity": "warning",
                "summary": "Triggers with no conditions (fires every eligible turn)",
                "triggers": unconditioned,
                "suggestion": (
                    "Add conditions to limit when these triggers fire, "
                    "or verify this is intentional."
                ),
            }
        )

    # Characters with no tracked item overrides when items use initialValueBasedOnPC="character".
    # Build the per-character item id→name map once, then check each character against it.
    per_char_items = {
        ti.get("id"): ti.get("name", ti.get("id"))
        for ti in world.get("trackedItems", [])
        if ti.get("initialValueBasedOnPC") == "character"
    }
    if per_char_items:
        per_char_ids = set(per_char_items)
        for ch in world.get("possibleCharacters", []):
            override_ids = {itv.get("id") for itv in ch.get("initialTrackedItemValues", [])}
            missing = per_char_ids - override_ids
            if missing:
                missing_names = [per_char_items[tid] for tid in missing]
                findings.append(
                    {
                        "type": "missing_per_character_overrides",
                        "severity": "warning",
                        "summary": (
                            f"Character '{ch.get('name', '?')}' missing "
                            "initialTrackedItemValues overrides"
                        ),
                        "items": missing_names,
                        "suggestion": (
                            "Add initialTrackedItemValues entries for per-character tracked items."
                        ),
                    }
                )

    # triggerOnTrackedItem conditions that test a menu-backed (pick-one) item.
    # The condition evaluates the player's single CHOSEN value, so it is not
    # always-true just because the option array lists requiredValue. Surfacing
    # the menu here prevents the common "always clobbered at game start" misread.
    menu_items = _menu_backed_items(world)
    if menu_items:
        for te in world.get("triggerEvents", []):
            tname = te.get("name", te.get("id", "?"))
            for cond in _iter_leaf_conditions(te.get("triggerConditions", [])):
                if cond.get("type") != "triggerOnTrackedItem":
                    continue
                raw_data = cond.get("data")
                data = raw_data if isinstance(raw_data, dict) else {}
                tid = cond.get("trackedItemID") or data.get("trackedItemID")
                if tid not in menu_items:
                    continue
                item = menu_items[tid]
                options = item["options"]
                comparison = data.get("textComparison") or data.get("inequality") or "?"
                required = data.get("requiredValue", "?")
                findings.append(
                    {
                        "type": "menu_backed_condition",
                        "severity": "info",
                        "summary": (
                            f"Trigger '{tname}' tests menu-backed tracked item "
                            f"'{item['name']}' (player picks one of {options})"
                        ),
                        "detail": (
                            f"'{item['name']}' ({tid}) is a per-character pick-one selection "
                            f"menu: the player selects exactly one of {options} at character "
                            f"selection, and that single choice becomes the active value. The "
                            f"condition ({comparison} '{required}') is evaluated against the "
                            "player's chosen value, so it fires ONLY for players whose choice "
                            f"matches — it is NOT always-true merely because the menu lists "
                            f"'{required}'. Reason about which single option satisfies it before "
                            "concluding the trigger always (or never) fires."
                        ),
                        "trigger": tname,
                        "trackedItem": item["name"],
                        "options": options,
                    }
                )

    return json.dumps({"findings": findings}, indent=2)


def _diff_value(a: Any, b: Any, path: str, changes: list[dict]) -> None:
    """Recursively diff two values, recording changes."""
    if not isinstance(b, type(a)) and not isinstance(a, type(b)):
        changes.append(
            {
                "path": path,
                "type": "type_change",
                "from": type(a).__name__,
                "to": type(b).__name__,
            }
        )
        return

    if isinstance(a, dict):
        all_keys = set(a.keys()) | set(b.keys())
        for k in sorted(all_keys):
            if k not in a:
                changes.append({"path": f"{path}.{k}", "type": "added", "value": b[k]})
            elif k not in b:
                changes.append({"path": f"{path}.{k}", "type": "removed", "value": a[k]})
            else:
                _diff_value(a[k], b[k], f"{path}.{k}", changes)
    elif isinstance(a, list):
        # For named entity arrays, try to diff by id/name; otherwise diff by index.
        # Check either side for the representative element shape.
        _rep = (a[0] if a else b[0]) if (a or b) else None
        is_entity_list = (
            _rep is not None and isinstance(_rep, dict) and ("id" in _rep or "name" in _rep)
        )
        if is_entity_list:
            id_key = "id" if "id" in _rep else "name"

            def _has_key(item: Any) -> bool:
                return isinstance(item, dict) and id_key in item

            a_map = {item[id_key]: item for item in a if _has_key(item)}
            b_map = {item[id_key]: item for item in b if _has_key(item)}
            for key in sorted(set(a_map.keys()) | set(b_map.keys()), key=str):
                if key not in a_map:
                    changes.append({"path": f"{path}[{id_key}={key}]", "type": "added"})
                elif key not in b_map:
                    changes.append({"path": f"{path}[{id_key}={key}]", "type": "removed"})
                else:
                    _diff_value(a_map[key], b_map[key], f"{path}[{id_key}={key}]", changes)

            # Entities lacking the chosen key can't be matched by id — compare them
            # positionally so they aren't silently dropped from the diff.
            a_rest = [item for item in a if not _has_key(item)]
            b_rest = [item for item in b if not _has_key(item)]
            if a_rest != b_rest:
                _diff_value(a_rest, b_rest, f"{path}[unkeyed]", changes)
        elif a != b:
            changes.append({"path": path, "type": "changed", "from": a, "to": b})
    else:
        if a != b:
            _from = str(a)[:100] if isinstance(a, str) and len(str(a)) > 100 else a
            _to = str(b)[:100] if isinstance(b, str) and len(str(b)) > 100 else b
            changes.append({"path": path, "type": "changed", "from": _from, "to": _to})


def compare_worlds(world_path_a: str, world_path_b: str) -> str:
    """Structural diff between two worlds. Returns JSON with additions, removals, and changes."""
    try:
        world_a = _load_world(world_path_a)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return json.dumps({"error": f"World A: {exc}"})
    try:
        world_b = _load_world(world_path_b)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return json.dumps({"error": f"World B: {exc}"})

    changes: list[dict] = []
    _diff_value(world_a, world_b, "(root)", changes)

    return json.dumps(
        {
            "world_a": world_path_a,
            "world_b": world_path_b,
            "total_changes": len(changes),
            "changes": changes,
        },
        indent=2,
    )


def get_diff_summary(original_path: str, current_path: str) -> str:
    """Human-readable narrative summary of changes between two worlds — for the author to read."""
    try:
        original = _load_world(original_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return f"**Error loading original**: {exc}"
    try:
        current = _load_world(current_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return f"**Error loading current**: {exc}"

    changes: list[dict] = []
    _diff_value(original, current, "(root)", changes)

    if not changes:
        return "No differences found between the two worlds."

    original_title = original.get("title", original_path)
    current_title = current.get("title", current_path)
    lines = [
        f"## Changes: {original_title} → {current_title}\n",
        f"**{len(changes)} change(s) detected**\n",
    ]

    # Group by category
    scalar_changes = [
        c for c in changes if c["type"] == "changed" and not c["path"].startswith("(root).[")
    ]
    array_adds = [c for c in changes if c["type"] == "added"]
    array_removes = [c for c in changes if c["type"] == "removed"]
    other = [c for c in changes if c not in scalar_changes + array_adds + array_removes]

    if scalar_changes:
        lines.append("### Modified fields")
        for ch in scalar_changes[:20]:  # cap at 20 for readability
            lines.append(f"- `{ch['path']}`: changed")
        if len(scalar_changes) > 20:
            lines.append(f"- *(and {len(scalar_changes) - 20} more)*")
        lines.append("")

    if array_adds:
        lines.append("### Added entities")
        for ch in array_adds[:20]:
            lines.append(f"- `{ch['path']}`")
        if len(array_adds) > 20:
            lines.append(f"- *(and {len(array_adds) - 20} more)*")
        lines.append("")

    if array_removes:
        lines.append("### Removed entities")
        for ch in array_removes[:20]:
            lines.append(f"- `{ch['path']}`")
        if len(array_removes) > 20:
            lines.append(f"- *(and {len(array_removes) - 20} more)*")
        lines.append("")

    if other:
        lines.append("### Other changes")
        for ch in other[:10]:
            lines.append(f"- `{ch['path']}` ({ch['type']})")
        lines.append("")

    return "\n".join(lines)
