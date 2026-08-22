"""Helper tools: create_new_world_json, make_draft_world, mint_ids, confirm_path."""

from __future__ import annotations

import copy
import json
import os
import re
import secrets
import shutil
import string
import uuid
from pathlib import Path
from typing import Any

from iw_architect import KNOWN_SCHEMA_VERSION
from iw_architect.paths import RelativePathError, relative_path_message, require_absolute

# Platform ID formats derived from the v2.2 fixture samples:
#   8-char: characters, triggers       — alphanumeric (A-Za-z0-9)
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

# Alphanumeric-only charset (A-Za-z0-9, 62 chars).
# Base64 chars (+, /) are intentionally excluded: IW silently renames tracked-item IDs that
# contain non-alphanumeric characters on import (confirmed via import test, June 2026),
# WITHOUT updating trigger references — leaving dangling refs and broken triggers.
_ID_CHARS = string.ascii_letters + string.digits


def _random_short_id(length: int) -> str:
    """Generate a random ID of the given length using the platform's observed character set."""
    return "".join(secrets.choice(_ID_CHARS) for _ in range(length))


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
    # `version` is intentionally the FIRST key so an author can see the world's
    # version at a glance the moment they open the raw JSON. Key order has no effect
    # on how IW interprets a world (it parses the file into an object), but IW does
    # renormalize top-level order to its own canonical order on import — where `version`
    # actually sorts near the end, before `designNotes`. So this front-placement is a
    # local, pre-import authoring convenience that IW undoes on import; it never reaches
    # exported worlds. See references/mechanics/PLATFORM_BEHAVIOR_NOTES.md ("Canonical
    # JSON Field Ordering"). The `make_draft_world` tool relocates `version` to the top
    # too, so drafts derived from existing worlds match scaffolded ones.
    "version": "1.00",
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
    "showPawScriptButtons": False,
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
    # KB v2.8 rec 6: seed at least one skill string — an empty array may break IW import.
    # (KB-empirical; iw_knowledge_base_v2_8.md). The value "General" matches the KB's own seed.
    "skills": ["General"],
    "possibleCharacters": [],
    "NPCs": [],
    "trackedItems": [],
    "triggerEvents": [],
    "instructionBlocks": [],
    "loreBookEntries": [],
    # schema v2.4: the named-event registry backing `triggerOnEvent` conditions. Seeded
    # empty rather than omitted so authors see the field exists and keep it in sync with
    # their triggerOnEvent strings (matched by exact text).
    "conditions": [],
    "allowChangeCharacterName": True,
    "allowChangeCharacterDescription": True,
    "allowChangeCharacterSkills": False,
    "allowChangeCharacterItemValues": False,
    "allowChangeCharacterPortrait": False,
    "allowChangeCharacterNewPortrait": False,
    "permissionsOnceShared": {"sharing": True, "editing": True},
    "autoAdvanceVersion": True,
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
    try:
        path = require_absolute(output_path)
    except RelativePathError as exc:
        return json.dumps({"error": str(exc)})
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


# IW displays world versions to two decimal places (`1.09`, `1.10`); a shorter minor
# component is a trailing-zero version with the zero dropped (`1.3` is 1.30).
_MIN_MINOR_WIDTH = 2


def _bump_version_component(version: str) -> str | None:
    """Increment the trailing dot-separated numeric component, preserving zero-pad width.

    ``"1.04"`` → ``"1.05"``, ``"2.09"`` → ``"2.10"``, ``"1.99"`` → ``"1.100"``,
    ``"5"`` → ``"6"``. Returns ``None`` if the trailing component is not purely numeric,
    so the caller can leave a non-standard version string untouched.

    IW world versions are two-decimal-place numbers (``1.09``, ``1.10``, …), so a
    single-digit component after a dot is a trailing-zero version shown without its
    zero: ``"1.3"`` is 1.30. It is widened to two places before the increment —
    ``"1.3"`` → ``"1.31"``, not ``"1.4"`` — so the bump is +0.01, never +0.10.
    Platform-confirmed 2026-08: the canonical fixture's IW export went ``1.09`` →
    ``"1.1"``, so the dropped trailing zero is how IW writes the version, not a
    hand-edit.
    """
    parts = version.split(".")
    last = parts[-1]
    if not last.isdigit():
        return None
    if len(parts) > 1 and len(last) < _MIN_MINOR_WIDTH:
        last = last.ljust(_MIN_MINOR_WIDTH, "0")
    parts[-1] = str(int(last) + 1).zfill(len(last))
    return ".".join(parts)


def _derive_draft_path(source: Path) -> Path:
    """Derive a ``_draft`` sibling path, incrementing any trailing ``_v<ver>`` filename token.

    ``world.json`` → ``world_draft.json``;
    ``world_v1.21.json`` → ``world_v1.22_draft.json``;
    ``world_v1.99.json`` → ``world_v1.100_draft.json``.
    """
    stem = source.stem
    match = re.search(r"_v(\d+(?:\.\d+)*)$", stem)
    if match:
        bumped = _bump_version_component(match.group(1))
        if bumped is not None:
            stem = stem[: match.start()] + "_v" + bumped
    return source.with_name(f"{stem}_draft{source.suffix}")


def _move_version_to_top(text: str, new_value: str) -> str | None:
    """Set the top-level ``version`` value and relocate its line to the first property.

    Pure line surgery — never a JSON parse/reserialize — so every line except ``version`` is
    left exactly as written, and unknown platform-managed fields survive untouched. Assumes a
    pretty-printed
    object whose top-level keys share one indentation level (what IW exports and what
    ``create_new_world_json`` writes). Returns ``None`` if the top-level ``version`` line
    can't be located for safe surgery (e.g. single-line JSON), so the caller can report
    rather than risk a malformed write.
    """
    lines = text.splitlines(keepends=True)

    brace_idx = next((i for i, ln in enumerate(lines) if ln.strip().endswith("{")), None)
    if brace_idx is None:
        return None

    # Top-level keys share the indentation of the first property after the opening brace.
    base_indent: str | None = None
    for ln in lines[brace_idx + 1 :]:
        if ln.strip():
            base_indent = ln[: len(ln) - len(ln.lstrip(" "))]
            break
    if base_indent is None:
        return None

    ver_idx: int | None = None
    for i in range(brace_idx + 1, len(lines)):
        ln = lines[i]
        indent = ln[: len(ln) - len(ln.lstrip(" "))]
        if indent == base_indent and re.match(r'\s*"version"\s*:', ln):
            ver_idx = i
            break
    if ver_idx is None:
        return None

    had_trailing_comma = bool(re.search(r",\s*$", lines[ver_idx]))
    # `version` is the sole top-level property when it has no trailing comma AND the only
    # line before it is the opening brace. The relocated line must then carry NO comma, or
    # we'd emit `{ "version": ..., }` — invalid JSON. (Unreachable for a real IW world, but
    # the function still must not produce malformed output for a degenerate input.)
    is_sole_property = not had_trailing_comma and ver_idx - 1 == brace_idx
    new_line = f'{base_indent}"version": {json.dumps(new_value)}{"" if is_sole_property else ","}\n'

    # If `version` was the last property (no trailing comma) but not the only one, the
    # property before it becomes the new last and must shed its trailing comma.
    if not had_trailing_comma and not is_sole_property:
        lines[ver_idx - 1] = re.sub(r",(\s*)$", r"\1", lines[ver_idx - 1])

    del lines[ver_idx]
    lines.insert(brace_idx + 1, new_line)
    return "".join(lines)


def make_draft_world(source_path: str, draft_path: str | None = None) -> str:
    """Copy an existing world to a working draft, protecting the source from edits.

    Copies ``source_path`` verbatim (``shutil.copy2``), then bumps the copy's in-file
    ``version`` (incrementing the trailing dot-separated component, preserving zero-pad)
    and relocates ``version`` to the first key so the author sees it the moment they open
    the raw file. **The source file is never modified** — it stays the clean, last-known-good
    diff baseline. This is the single entry point for the ``/modify-world`` draft step and
    the ``/spinoff-world`` copy step.

    source_path: absolute path to the existing world JSON to protect and copy.
    draft_path: absolute destination for the copy. Omit it (the ``/modify-world`` default)
        to derive a sibling ``_draft`` path, incrementing any trailing ``_v<ver>`` filename
        token (``world_v1.21.json`` → ``world_v1.22_draft.json``). Pass it explicitly for a
        ``/spinoff-world`` variant whose name the author chose.

    Pass-through preservation: the copy is a real file copy and the only content change is to
    the ``version`` line — never a JSON parse/reserialize — so all other formatting and any
    unknown platform-managed fields are preserved (IW worlds are LF-newline JSON). Run
    ``validate_world`` on the returned draft path to confirm it is clean.

    If the source has no string ``version`` field (or a non-numeric one), it is copied
    unchanged: no key is bumped, moved, or injected.
    """
    try:
        source = require_absolute(source_path)
    except RelativePathError as exc:
        return json.dumps({"error": str(exc)})
    if not source.is_file():
        return json.dumps({"error": f"Source world not found: {source}"})

    if draft_path is None:
        dest = _derive_draft_path(source)
    else:
        try:
            dest = require_absolute(draft_path)
        except RelativePathError as exc:
            return json.dumps({"error": str(exc)})

    if dest.resolve() == source.resolve():
        return json.dumps({"error": "draft_path must differ from the source path."})
    if not dest.parent.exists():
        return json.dumps({"error": f"Parent directory does not exist: {dest.parent}"})
    if dest.exists():
        return json.dumps(
            {
                "error": (
                    f"Refusing to overwrite existing file: {dest}. Choose a different draft_path."
                )
            }
        )

    shutil.copy2(source, dest)
    text = dest.read_text()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return json.dumps(
            {
                "status": "copied",
                "source_path": str(source),
                "draft_path": str(dest),
                "version": None,
                "message": (
                    f"Copied, but the source is not valid JSON ({exc}); left it untouched. "
                    "Run validate_world to see the errors."
                ),
            }
        )

    old_version = data.get("version")
    if not isinstance(old_version, str):
        return json.dumps(
            {
                "status": "drafted",
                "source_path": str(source),
                "draft_path": str(dest),
                "version": None,
                "message": (
                    "Copied. Source has no string `version` field, so none was bumped or "
                    "moved. Run validate_world on the draft to confirm."
                ),
            }
        )

    new_version = _bump_version_component(old_version)
    moved_text = _move_version_to_top(text, new_version) if new_version is not None else None
    if new_version is None or moved_text is None:
        reason = (
            f"`version` ({old_version!r}) has a non-numeric trailing component"
            if new_version is None
            else "could not locate the top-level `version` line to edit without reformatting"
        )
        return json.dumps(
            {
                "status": "drafted",
                "source_path": str(source),
                "draft_path": str(dest),
                "version": {"from": old_version, "to": old_version},
                "message": (
                    f"Copied, but {reason}; left `version` as-is (not bumped or moved). "
                    "Adjust it manually if needed, then run validate_world."
                ),
            }
        )

    dest.write_text(moved_text)
    return json.dumps(
        {
            "status": "drafted",
            "source_path": str(source),
            "draft_path": str(dest),
            "version": {"from": old_version, "to": new_version},
            "message": (
                f"Drafted {dest.name}: copied from the source, bumped version "
                f"{old_version} → {new_version}, and moved `version` to the first key. "
                "The source is untouched. Run validate_world on the draft to confirm."
            ),
        }
    )


def confirm_path(path: str) -> str:
    """Verify an absolute path exists (or its parent does) and echo it back for confirmation.

    Requires an **absolute** path (a leading ``~`` is expanded to the home directory first).
    Relative paths are rejected with an actionable error: this tool runs inside the MCP server
    process, whose working directory is not your session's, so a relative path cannot be
    resolved to the file the author means. Resolve the path to an absolute path in your session
    first (e.g. join it with your current working directory), then call this. Does not modify
    any files.
    """
    expanded = Path(os.path.expanduser(path))
    if not expanded.is_absolute():
        return json.dumps(
            {
                "input_path": path,
                "resolved_path": None,
                "is_absolute": False,
                "server_cwd": os.getcwd(),
                "status": "error",
                "message": relative_path_message(path),
            }
        )

    resolved = expanded.resolve()
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
