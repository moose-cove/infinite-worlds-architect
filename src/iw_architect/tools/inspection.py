"""Inspection tools: read_world_field, format_world_for_review, get_schema_summary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from iw_architect.paths import require_absolute
from iw_architect.schema_model import SCHEMA_SUMMARY


def _load_world(world_path: str) -> dict:
    path = require_absolute(world_path)
    if not path.exists():
        raise FileNotFoundError(f"World file not found: {world_path}")
    return json.loads(path.read_text())


def _resolve_path(world: dict, path: str) -> Any:
    """Navigate a world dict using dot/bracket path syntax.

    Supports:
      background                         simple key
      imagePromptDetails.illustrGenre    dotted nesting
      NPCs[name=Finnegan Mosswood]       name-bracket lookup
      triggerEvents[0].name              index-bracket + dotted
      possibleCharacters[characterId=x]  arbitrary field bracket
    """
    # Tokenize the path into steps
    # Steps are: bare keys, [n] index steps, [field=value] lookup steps
    steps: list[str | int | tuple[str, str]] = []
    remaining = path.strip()

    while remaining:
        # Bracket step: [n] or [field=value]
        m = re.match(r"^\[([^\]]+)\](.*)", remaining)
        if m:
            inside, remaining = m.group(1), m.group(2).lstrip(".")
            if re.fullmatch(r"\d+", inside):
                steps.append(int(inside))
            elif "=" in inside:
                field, value = inside.split("=", 1)
                steps.append((field.strip(), value.strip()))
            else:
                raise ValueError(f"Unparseable bracket step: [{inside}]")
            continue

        # Dotted key step
        m = re.match(r"^([^.[]+)(.*)", remaining)
        if m:
            key_part = m.group(1)
            rest = m.group(2)
            steps.append(key_part)
            remaining = rest.lstrip(".")
            continue

        raise ValueError(f"Cannot parse path at: {remaining!r}")

    current: Any = world
    for step in steps:
        if isinstance(step, str):
            if not isinstance(current, dict):
                raise ValueError(f"Cannot access key '{step}' on non-dict value")
            current = current[step]
        elif isinstance(step, int):
            if not isinstance(current, list):
                raise ValueError("Cannot index a non-list value")
            current = current[step]
        else:
            field_name, field_value = step
            if not isinstance(current, list):
                raise ValueError(f"Cannot do [{field_name}=...] lookup on non-list")
            matches = [item for item in current if str(item.get(field_name, "")) == field_value]
            if not matches:
                raise KeyError(f"No entity with {field_name}={field_value!r}")
            current = matches[0]

    return current


def read_world_field(world_path: str, path: str) -> str:
    """Read a single field from a world JSON by path.

    Path syntax examples:
      background
      imagePromptDetails.illustrGenre
      NPCs[name=Finnegan Mosswood].location
      triggerEvents[0].name
      possibleCharacters[characterId=0TBwVqX9].skills
    """
    try:
        world = _load_world(world_path)
    except FileNotFoundError as exc:
        return json.dumps({"error": str(exc)})
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    try:
        value = _resolve_path(world, path)
        return json.dumps({"path": path, "value": value}, indent=2)
    except (KeyError, IndexError, ValueError) as exc:
        return json.dumps({"error": str(exc), "path": path})


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n" if body.strip() else ""


def _cond_summary(cond: dict, indent: int = 0) -> str:
    pad = "  " * indent
    cat = cond.get("category", "?")
    if cat == "logic":
        op = cond.get("operator", "and").upper()
        sub = cond.get("data", [])
        sub_lines = "\n".join(_cond_summary(s, indent + 1) for s in sub)
        return f"{pad}[{op}]\n{sub_lines}"
    ctype = cond.get("type", "?")
    data = cond.get("data")
    return f"{pad}- {ctype}: {json.dumps(data, ensure_ascii=False)}"


def _effect_summary(effect: dict) -> str:
    etype = effect.get("type", "?")
    data = effect.get("data")
    if isinstance(data, str) and len(data) > 80:
        data = data[:77] + "..."
    return f"- **{etype}**: {json.dumps(data, ensure_ascii=False)}"


def _render_world_markdown(world: dict) -> str:
    """Build the human-readable Markdown body for a loaded world dict."""
    parts: list[str] = []

    parts.append(f"# {world.get('title', '(Untitled)')}\n")
    parts.append(f"**Schema version**: {world.get('schemaVersion', '?')}  ")
    parts.append(
        f"**Mature**: {world.get('mature', False)}  **NSFW**: {world.get('nsfw', False)}\n"
    )

    if desc := world.get("description"):
        parts.append(_section("Description", desc))
    if bg := world.get("background"):
        parts.append(_section("Background", bg))
    if instr := world.get("instructions"):
        parts.append(_section("Main Instructions", instr))
    if style := world.get("authorStyle"):
        parts.append(f"**Author style**: {style}\n")
    if obj := world.get("objective"):
        parts.append(_section("Objective", obj))
    if fi := world.get("firstInput"):
        parts.append(_section("First Action (hidden turn-0 prompt)", fi))

    # Skills
    skills = world.get("skills", [])
    if skills:
        parts.append(f"## Skills\n\n{', '.join(skills)}\n")

    # Characters
    chars = world.get("possibleCharacters", [])
    if chars:
        lines = ["## Player Characters\n"]
        for ch in chars:
            lines.append(f"### {ch.get('name', '?')}")
            if cid := ch.get("characterId"):
                lines.append(f"*ID: {cid}*")
            if d := ch.get("description"):
                lines.append(d)
            if s := ch.get("skills"):
                lines.append(f"Skills: {', '.join(f'{k}: {v}' for k, v in s.items())}")
            lines.append("")
        parts.append("\n".join(lines))

    # NPCs
    npcs = world.get("NPCs", [])
    if npcs:
        lines = ["## NPCs\n"]
        for npc in sorted(npcs, key=lambda n: n.get("positionInList", 0)):
            lines.append(f"### {npc.get('name', '?')}")
            if nid := npc.get("id"):
                lines.append(f"*ID: {nid}*")
            if ol := npc.get("one_liner"):
                lines.append(f"*{ol}*")
            if detail := npc.get("detail"):
                lines.append(detail)
            lines.append("")
        parts.append("\n".join(lines))

    # Tracked items
    items = world.get("trackedItems", [])
    if items:
        lines = ["## Tracked Items\n"]
        for ti in sorted(items, key=lambda t: t.get("positionInList", 0)):
            name = ti.get("name", "?")
            tid = ti.get("id", "?")
            dtype = ti.get("dataType", "?")
            vis = ti.get("visibility", "?")
            init = ti.get("initialValue", "")
            lines.append(f"### {name}")
            lines.append(f"*ID: {tid} | type: {dtype} | visibility: {vis} | initial: {init!r}*")
            if desc := ti.get("description"):
                lines.append(desc)
            lines.append("")
        parts.append("\n".join(lines))

    # Trigger events
    triggers = world.get("triggerEvents", [])
    if triggers:
        lines = ["## Trigger Events\n"]
        for te in triggers:
            tname = te.get("name", "?")
            tid = te.get("id", "?")
            lines.append(f"### {tname}")
            lines.append(f"*ID: {tid}*")
            flags = []
            if te.get("triggerOnStartOfGame"):
                flags.append("fires at start of game")
            if te.get("canTriggerMoreThanOnce"):
                flags.append("can repeat")
            if te.get("advancedLogic"):
                flags.append("advanced logic")
            if flags:
                lines.append(f"*Flags: {', '.join(flags)}*")

            conditions = te.get("triggerConditions", [])
            if conditions:
                lines.append("**Conditions:**")
                for cond in conditions:
                    lines.append(_cond_summary(cond, indent=1))

            effects = te.get("triggerEffects", [])
            if effects:
                lines.append("**Effects:**")
                for eff in effects:
                    lines.append(_effect_summary(eff))
            lines.append("")
        parts.append("\n".join(lines))

    # Instruction blocks
    ibs = world.get("instructionBlocks", [])
    if ibs:
        lines = ["## Instruction Blocks (always-active)\n"]
        for ib in ibs:
            lines.append(f"### {ib.get('name', '?')} *(id: {ib.get('id', '?')})*")
            if profiles := ib.get("selectedAIProfiles"):
                lines.append(f"*AI profiles: {', '.join(profiles)}*")
            lines.append(ib.get("content", ""))
            lines.append("")
        parts.append("\n".join(lines))

    # Lore book entries
    lbe = world.get("loreBookEntries", [])
    if lbe:
        lines = ["## Lore Book Entries (keyword-triggered)\n"]
        for lb in lbe:
            kw = ", ".join(f'"{k}"' for k in lb.get("keywords", []))
            lines.append(f"### {lb.get('name', '?')} *(id: {lb.get('id', '?')})*")
            lines.append(f"*Keywords: {kw}*")
            lines.append(lb.get("content", ""))
            lines.append("")
        parts.append("\n".join(lines))

    # Victory / defeat
    for key, label in (("victoryCondition", "Victory"), ("defeatCondition", "Defeat")):
        cond = world.get(key)
        if cond and isinstance(cond, dict):
            parts.append(f"## {label} Condition\n")
            parts.append(f"**Trigger**: {cond.get('condition', '')}")
            parts.append(f"**Message**: {cond.get('text', '')}\n")

    # Notes
    if notes := world.get("designNotes"):
        parts.append(_section("Design Notes (not sent to AI)", notes))

    return "\n".join(parts)


def format_world_for_review(world_path: str) -> str:
    """Render the world as Markdown and write it to a sibling `.review.md` file.

    Writes the rendered review to `<world_stem>.review.md` next to the input
    world JSON, so the markdown does not flood the calling agent's context.

    Returns a JSON envelope:
      {"success": "<absolute path to .review.md>"} on success
      {"error": "<details>"} on failure (missing file, invalid JSON, write error)
    """
    try:
        world = _load_world(world_path)
    except FileNotFoundError as exc:
        return json.dumps({"error": str(exc)})
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON in world file: {exc}"})
    except OSError as exc:
        return json.dumps({"error": f"Failed to read world file: {exc}"})

    try:
        markdown = _render_world_markdown(world)
        output_path = Path(world_path).resolve().with_suffix(".review.md")
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return json.dumps({"error": f"Failed to write review file: {exc}"})

    return json.dumps({"success": str(output_path)})


# Story-extraction tools surfaced for discoverability via get_schema_summary (D4).
# These are tools, not world fields, so they are merged into the summary output
# here rather than added to the schema JSON (which is derived solely from the world
# schema). Kept inline — not imported from tools.story_tools — to avoid a circular
# import, since story_tools imports _load_world from this module.
_STORY_TOOL_SUMMARIES: list[dict[str, str]] = [
    {
        "name": "extract_story_data",
        "purpose": (
            "Parse Infinite Worlds story-export .txt files into structured JSON "
            "(manifest, metadata, turn index, tracked-item snapshots, optional "
            "character index) for building a sequel world."
        ),
    },
    {
        "name": "query_story_data",
        "purpose": (
            "Read back a slice of an extraction directory by category (manifest | "
            "metadata | turn_index | tracked_state | turn_detail | character_index), "
            "optionally filtered to specific turns."
        ),
    },
    {
        "name": "get_character_list",
        "purpose": (
            "Derive a starting character list (player characters + NPCs) from an "
            "original world JSON, for confirmation before character indexing."
        ),
    },
]


def get_schema_summary() -> str:
    """Return the canonical schema as structured JSON — entity types, fields, enums, etc.

    Also surfaces an ``availableTools`` list of the story-extraction tools so the
    sequel-world workflow can discover them without a separate prompt (design
    decision D4). They are merged into the output here rather than added to the
    schema JSON because they are tools, not world fields.
    """
    summary = {**SCHEMA_SUMMARY, "availableTools": _STORY_TOOL_SUMMARIES}
    return json.dumps(summary, indent=2)
