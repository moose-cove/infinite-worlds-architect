"""Helper tools: create_new_world_json, mint_ids, confirm_path."""

from __future__ import annotations

import copy
import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Any

from iw_architect import KNOWN_SCHEMA_VERSION

# Platform ID formats derived from the v2.1 fixture samples:
#   8-char: characters, triggers       — base64 character set (A-Za-z0-9+/)
#   9-char: NPCs, trackedItems, instruction/lore blocks — same character set
#   UUID:   trigger conditions and effects
_ENTITY_ID_LENGTHS: dict[str, int | None] = {
    "character": 8,
    "npc": 9,
    "trackedItem": 9,
    "triggerEvent": 8,
    "triggerStep": None,  # UUID
    "instructionBlock": 9,
    "loreBookEntry": 9,
}

_B64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _random_short_id(length: int) -> str:
    """Generate a random ID of the given length using the platform's observed character set."""
    return "".join(secrets.choice(_B64_CHARS) for _ in range(length))


def mint_ids(kind: str, count: int = 1) -> str:
    """Generate IDs in the format the platform expects for the given entity kind.

    kind: one of character, npc, trackedItem, triggerEvent, triggerStep,
        instructionBlock, loreBookEntry
    count: how many IDs to generate (default 1)
    Returns a JSON array of ID strings.
    """
    if kind not in _ENTITY_ID_LENGTHS:
        return json.dumps(
            {"error": f"Unknown kind '{kind}'. Valid kinds: {sorted(_ENTITY_ID_LENGTHS)}"}
        )
    if not isinstance(count, int) or count < 1:
        return json.dumps({"error": "count must be a positive integer"})
    if count > 100:
        return json.dumps({"error": "count must not exceed 100"})

    length = _ENTITY_ID_LENGTHS[kind]
    ids: list[str] = []
    for _ in range(count):
        if length is None:
            ids.append(str(uuid.uuid4()))
        else:
            ids.append(_random_short_id(length))

    return json.dumps({"kind": kind, "ids": ids})


_DEFAULT_SCAFFOLD: dict[str, Any] = {
    "schemaVersion": KNOWN_SCHEMA_VERSION,
    "title": "",
    "description": "",
    "background": "",
    "instructions": "",
    "authorStyle": "",
    "firstInput": "",
    "objective": "",
    "mature": False,
    "nsfw": False,
    "contentWarnings": "",
    "designNotes": "",
    "charSelectText": "",
    "enableAISpecificInstructionBlocks": False,
    "recommendedAIModel": None,
    "hideSkillSystem": False,
    "imageModel": "manticore",
    "imageStyle": "photo_1",
    "imageStyleCharacterPre": "A beautiful medium shot photographic portrait of",
    "imageStyleCharacterPost": (
        "The focus is razor-sharp on the texture of the face, showing every pore. "
        "IWBeautiful IWUpscaleFace"
    ),
    "imageStyleNonCharacterPre": "A beautiful photograph of",
    "imageStyleNonCharacterPost": "",
    "illustrationStyleCharacterLowPriority": "",
    "illustrationStyleCharacterHighPriority": "",
    "illustrationStyleNonCharacterLowPriority": "",
    "illustrationStyleNonCharacterHighPriority": "",
    "skills": [],
    "possibleCharacters": [],
    "NPCs": [],
    "trackedItems": [],
    "triggerEvents": [],
    "instructionBlocks": [],
    "loreBookEntries": [],
    "allowChangeCharacterName": True,
    "allowChangeCharacterDescription": True,
    "allowChangeCharacterSkills": False,
    "allowChangeCharacterItemValues": False,
    "allowChangeCharacterPortrait": False,
    "allowChangeCharacterNewPortrait": False,
    "permissionsOnceShared": {"sharing": True, "editing": True},
    "autoAdvanceVersion": True,
    "version": "1.00",
}


def create_new_world_json(
    output_path: str,
    title: str = "Untitled World",
    nsfw: bool = False,
) -> str:
    """Create a fresh world JSON at the given path with sane defaults.

    The resulting file passes validate_world with zero errors.
    output_path: absolute path where the world JSON will be written
    title: initial title for the world
    nsfw: if true, sets both nsfw and mature to true
    """
    path = Path(output_path)
    if not path.parent.exists():
        return json.dumps({"error": f"Parent directory does not exist: {path.parent}"})

    # deepcopy, not dict(): _DEFAULT_SCAFFOLD holds nested mutable containers
    # (lists, the permissions dict) that a shallow copy would alias back to the
    # module-level constant. See rules/common/coding-style.md (immutability).
    world = copy.deepcopy(_DEFAULT_SCAFFOLD)
    world["title"] = title
    if nsfw:
        world["nsfw"] = True
        world["mature"] = True

    path.write_text(json.dumps(world, indent=2))
    return json.dumps(
        {
            "status": "created",
            "path": str(path.resolve()),
            "message": f"World '{title}' created at {path}. Run validate_world to confirm.",
        }
    )


def confirm_path(path: str) -> str:
    """Resolve a user-supplied path to an absolute path and verify it exists (or its parent does).

    Returns the resolved absolute path for the agent to present to the user for confirmation
    before acting on it. Does not modify any files.
    """
    resolved = Path(os.path.expanduser(path)).resolve()
    exists = resolved.exists()
    parent_exists = resolved.parent.exists()

    if not exists and not parent_exists:
        return json.dumps(
            {
                "resolved_path": str(resolved),
                "exists": False,
                "parent_exists": False,
                "status": "error",
                "message": f"Neither '{resolved}' nor its parent directory exists.",
            }
        )

    return json.dumps(
        {
            "resolved_path": str(resolved),
            "exists": exists,
            "parent_exists": parent_exists,
            "status": "ok",
            "message": (
                f"Path resolves to: {resolved}"
                + (
                    " (file exists)"
                    if exists
                    else " (parent directory exists, file not yet created)"
                )
            ),
        }
    )
