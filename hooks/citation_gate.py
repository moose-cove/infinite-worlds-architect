"""citation_gate.py — Stop hook enforcing story evidence citations.

Fired by Claude Code on every Stop event (session end / turn completion).
When the session-scoped arming flag exists this hook inspects the last
assistant message for any ``**Proposed Value:**`` blocks and verifies each
is followed by a well-formed ``**Evidence:**`` line in one of the four
accepted formats.

Architecture
------------
- ``evaluate(payload, project_dir)`` is a pure function: testable without
  subprocess or filesystem side-effects beyond reading the flag file.
- ``main()`` wires stdin/stdout/env to ``evaluate``.

Marker-file location
--------------------
``${CLAUDE_PROJECT_DIR}/.claude/sequel-world-active/<session_id>``

The gate is per-session: a missing file for the current session means the
hook no-ops entirely (even if another session's file exists). This prevents
a crash-without-disarm from poisoning every subsequent session.

Evidence formats (any of four accepted)
----------------------------------------
1. STORY CITATION  — starts with ``From Turn #<N>`` or ``From Story Metadata``
2. USER DIRECTED   — starts with ``USER_DIRECTED:`` followed by non-empty text
3. CARRY FORWARD   — starts with ``CARRY_FORWARD:`` followed by non-empty text
4. GAP FOUND       — starts with ``NO_STORY_EVIDENCE:`` followed by non-empty text

Pure stdlib only.  No third-party imports.  Target: <10 ms.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Matches a ``**Proposed Value:**`` heading and captures the field name from
# the preceding ``**Field:**`` line within the same block.
_PROPOSAL_BLOCK_RE = re.compile(
    r"\*\*Field:\*\*\s*(?P<field>[^\n]+)\n"  # **Field:** <name>
    r"\*\*Proposed Value:\*\*[^\n]*\n"  # **Proposed Value:** <value>
    r"(?P<after>.*?)(?=\*\*Field:\*\*|\Z)",  # everything until next block or end
    re.DOTALL,
)

# Matches the **Evidence:** line.
_EVIDENCE_LINE_RE = re.compile(r"\*\*Evidence:\*\*\s*(?P<body>.+)", re.MULTILINE)

# Valid evidence body patterns.
_STORY_CITATION_RE = re.compile(r"^From (Turn #\d+|Story Metadata)")
_USER_DIRECTED_RE = re.compile(r"^USER_DIRECTED:\s*\S")
_CARRY_FORWARD_RE = re.compile(r"^CARRY_FORWARD:\s*\S")
_GAP_FOUND_RE = re.compile(r"^NO_STORY_EVIDENCE:\s*\S")


# ---------------------------------------------------------------------------
# Pure evaluation logic (exported for tests)
# ---------------------------------------------------------------------------


def _is_valid_evidence(body: str) -> bool:
    """Return True if ``body`` matches one of the four accepted evidence formats."""
    b = body.strip()
    return bool(
        _STORY_CITATION_RE.match(b)
        or _USER_DIRECTED_RE.match(b)
        or _CARRY_FORWARD_RE.match(b)
        or _GAP_FOUND_RE.match(b)
    )


def evaluate(payload: dict, project_dir: str | None) -> dict | None:
    """Evaluate a Stop-hook payload.

    Returns a ``{"decision": "block", "reason": "..."}`` dict when the gate is
    armed and the message contains a poorly-cited proposal block; returns
    ``None`` in all pass/no-op cases.

    Parameters
    ----------
    payload:
        The parsed JSON object received on stdin from Claude Code.
    project_dir:
        Value of ``CLAUDE_PROJECT_DIR`` (``None`` when absent → no-op).
    """
    # --- Loop-safety guard: never re-block a hook that is already blocking ---
    if payload.get("stop_hook_active"):
        print(
            "citation_gate: stop_hook_active is true — skipping block to avoid loop",
            file=sys.stderr,
        )
        return None

    # --- Require CLAUDE_PROJECT_DIR ---
    if not project_dir:
        return None  # no-op; can't build flag path

    # --- Validate session_id to prevent path traversal ---
    session_id: object = payload.get("session_id")
    if not isinstance(session_id, str) or not _UUID_RE.match(session_id):
        return None  # no-op; untrusted / missing id

    # --- Check per-session arming flag ---
    flag_path = Path(project_dir) / ".claude" / "sequel-world-active" / session_id
    if not flag_path.exists():
        return None  # gate not armed for this session

    # --- Gate is armed; examine last_assistant_message ---
    message: object = payload.get("last_assistant_message", "")
    if not isinstance(message, str):
        return None

    # If there are no proposal blocks, nothing to check.
    if "**Proposed Value:**" not in message:
        return None

    # --- Parse all proposal blocks and verify each has valid evidence ---
    bad_fields: list[str] = []
    for match in _PROPOSAL_BLOCK_RE.finditer(message):
        field_name = match.group("field").strip()
        after_block = match.group("after")

        evidence_match = _EVIDENCE_LINE_RE.search(after_block)
        if evidence_match is None:
            bad_fields.append(field_name)
            continue

        body = evidence_match.group("body")
        if not _is_valid_evidence(body):
            bad_fields.append(field_name)

    if not bad_fields:
        return None  # all proposals are well-cited

    field_list = ", ".join(f'"{f}"' for f in bad_fields)
    reason = (
        f"Missing or malformed Evidence citation for field(s): {field_list}. "
        "Each **Proposed Value:** block must be immediately followed by "
        "**Evidence:** in one of these formats: "
        "'From Turn #<N> Outcome: ...' / 'From Story Metadata', "
        "'USER_DIRECTED: <reason>', "
        "'CARRY_FORWARD: <reason>', or "
        "'NO_STORY_EVIDENCE: <reason>'. "
        "See references/guidance/CITATION_METHODOLOGY.md."
    )
    return {"decision": "block", "reason": reason}


# ---------------------------------------------------------------------------
# CLI entry point (stdin → stdout)
# ---------------------------------------------------------------------------


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Can't parse stdin; no-op safely.
        return

    project_dir: str | None = os.environ.get("CLAUDE_PROJECT_DIR")

    result = evaluate(payload, project_dir)
    if result is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
