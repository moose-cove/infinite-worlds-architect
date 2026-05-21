"""Schema model — SCHEMA_SUMMARY derived from the JSON Schema document.

Per DESIGN_BRIEF_v2.md §7 milestone 2, schema knowledge lives in a single
representation. The JSON Schema artifact at
``skills/world-architect/references/world_v2.1.schema.json`` is the canonical
source; both the Tier 1 validator and ``get_schema_summary()`` consume it.

This module derives the ``SCHEMA_SUMMARY`` dict at import time by translating
JSON Schema constructs (``properties``, ``required``, ``enum``, ``$ref``,
``$defs``) plus IW-specific extensions (``x-iw-category``, ``x-iw-note``,
``x-iw-id-field``, ``x-iw-id-format``, ``x-iw-condition-types``,
``x-iw-effect-types``, ``x-iw-template-variables``) into the entity-centric
shape that the LLM-facing summary uses.

Adding a new platform field is a single-file change: edit the JSON Schema. The
derived ``SCHEMA_SUMMARY`` updates automatically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PLUGIN_ROOT = Path(__file__).parent.parent.parent
_SCHEMA_PATH = _PLUGIN_ROOT / "skills" / "world-architect" / "references" / "world_v2.1.schema.json"

# Top-level array properties whose items are $ref into $defs become entityTypes entries.
# The mapping connects the world-level field name (NPCs, trackedItems) with the $defs key.
_ENTITY_FIELDS_TO_DEF = {
    "possibleCharacters": "character",
    "NPCs": "npc",
    "trackedItems": "trackedItem",
    "triggerEvents": "triggerEvent",
    "instructionBlocks": "instructionBlock",
    "loreBookEntries": "loreBookEntry",
}


def _type_label(node: dict) -> str:
    """Return the short type label used by SCHEMA_SUMMARY for a JSON Schema node.

    Mirrors the labels in the previous hand-written SCHEMA_SUMMARY:
        {"type": "string"}                       → "string"
        {"type": ["string", "null"]}             → "string|null"
        {"type": "array", "items": {"type":"x"}} → "x[]"
        {"type": "array", "items": {"$ref":...}} → "object[]"
        {"$ref": ...}                            → "object"
        {"oneOf": [{"type":"null"},{"$ref":...}]} → "object|null"
    """
    if "$ref" in node:
        return "object"
    if "oneOf" in node:
        labels: list[str] = []
        has_null = False
        for alt in node["oneOf"]:
            if not isinstance(alt, dict):
                continue
            if alt.get("type") == "null":
                has_null = True
            else:
                labels.append(_type_label(alt))
        # Place null last for readability ("object|null" reads better than "null|object").
        if has_null:
            labels.append("null")
        return "|".join(labels) if labels else "object"
    raw_type = node.get("type")
    if isinstance(raw_type, list):
        return "|".join(raw_type)
    if raw_type == "array":
        items = node.get("items", {})
        if isinstance(items, dict):
            return f"{_type_label(items)}[]"
        return "array"
    if raw_type is None:
        # Untyped node with properties is effectively an object.
        if "properties" in node:
            return "object"
        return "object"
    return raw_type


def _build_field_entry(node: dict, *, required: bool = False) -> dict:
    """Build a single field metadata entry from a JSON Schema property node."""
    entry: dict[str, Any] = {"type": _type_label(node)}
    if required:
        entry["required"] = True
    if "x-iw-category" in node:
        entry["category"] = node["x-iw-category"]
    if "enum" in node:
        entry["enum"] = list(node["enum"])
    if "x-iw-note" in node:
        entry["note"] = node["x-iw-note"]
    if "default" in node:
        entry["default"] = node["default"]
    if "description" in node:
        entry["description"] = node["description"]
    return entry


def _build_fields_map(obj_schema: dict) -> dict[str, dict]:
    """Build a field-name → entry dict from a JSON Schema object schema's properties."""
    required_set = set(obj_schema.get("required", []))
    return {
        name: _build_field_entry(prop_node, required=name in required_set)
        for name, prop_node in obj_schema.get("properties", {}).items()
    }


def _build_entity_entry(def_node: dict) -> dict:
    entry: dict[str, Any] = {}
    if "description" in def_node:
        entry["description"] = def_node["description"]
    if "x-iw-id-field" in def_node:
        entry["idField"] = def_node["x-iw-id-field"]
    if "x-iw-id-format" in def_node:
        entry["idFormat"] = def_node["x-iw-id-format"]
    entry["fields"] = _build_fields_map(def_node)
    return entry


def _build_schema_summary(schema: dict) -> dict:
    """Derive the SCHEMA_SUMMARY structure from the JSON Schema document."""
    defs = schema.get("$defs", {})
    summary: dict[str, Any] = {
        "schemaVersion": schema.get("x-iw-schema-version", 2.1),
        "topLevelFields": _build_fields_map(schema),
        "entityTypes": {
            field_name: _build_entity_entry(defs[def_name])
            for field_name, def_name in _ENTITY_FIELDS_TO_DEF.items()
            if def_name in defs
        },
        "conditionTypes": dict(defs.get("triggerCondition", {}).get("x-iw-condition-types", {})),
        "effectTypes": dict(defs.get("triggerEffect", {}).get("x-iw-effect-types", {})),
        "templateVariables": dict(schema.get("x-iw-template-variables", {})),
    }
    return summary


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


# Computed once at import time. This is the canonical, JSON-Schema-derived
# summary consumed by get_schema_summary().
SCHEMA_SUMMARY: dict = _build_schema_summary(_load_schema())
