"""tests/test_citation_gate.py — unit tests for the citation gate Stop hook.

All tests target the pure ``evaluate(payload, project_dir)`` function exported
from ``hooks.citation_gate``.  No subprocess is spawned; filesystem interaction
is limited to creating the per-session flag file via ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# hooks/ is added to sys.path by tests/conftest.py before collection.
from citation_gate import evaluate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SESSION_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

GOOD_MESSAGE_STORY = """\
**Field:** title
**Proposed Value:** The Dragon's Keep
**Evidence:** From Turn #3 Outcome: The party reached the castle gates.
"""

GOOD_MESSAGE_METADATA = """\
**Field:** title
**Proposed Value:** The Dragon's Keep
**Evidence:** From Story Metadata
"""

GOOD_MESSAGE_USER_DIRECTED = """\
**Field:** objective
**Proposed Value:** Rescue the prisoner
**Evidence:** USER_DIRECTED: Author explicitly set this objective.
"""

GOOD_MESSAGE_CARRY_FORWARD = """\
**Field:** objective
**Proposed Value:** Find the artefact
**Evidence:** CARRY_FORWARD: Same objective as original world; no story contradiction.
"""

GOOD_MESSAGE_GAP = """\
**Field:** background
**Proposed Value:** A land of ice and fire
**Evidence:** NO_STORY_EVIDENCE: No background data in story export; using world source.
"""

BAD_MESSAGE_NO_EVIDENCE = """\
**Field:** title
**Proposed Value:** The Dragon's Keep
"""

BAD_MESSAGE_WRONG_PREFIX = """\
**Field:** title
**Proposed Value:** The Dragon's Keep
**Evidence:** I just made this up.
"""

MULTI_GOOD = """\
**Field:** title
**Proposed Value:** First World
**Evidence:** From Turn #1 Outcome: The story began here.

**Field:** description
**Proposed Value:** A dark realm
**Evidence:** CARRY_FORWARD: Same as original world.
"""

MULTI_BAD_SECOND = """\
**Field:** title
**Proposed Value:** First World
**Evidence:** From Turn #1 Outcome: The story began here.

**Field:** description
**Proposed Value:** A dark realm
"""

NO_PROPOSAL_MESSAGE = "Just a regular message with no proposals at all."


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def armed_dir(tmp_path: Path) -> tuple[Path, str]:
    """Return (project_dir, project_dir_str) with the flag armed for SESSION_A."""
    flag_dir = tmp_path / ".claude" / "sequel-world-active"
    flag_dir.mkdir(parents=True)
    (flag_dir / SESSION_A).touch()
    return tmp_path, str(tmp_path)


@pytest.fixture()
def unarmed_dir(tmp_path: Path) -> tuple[Path, str]:
    """Return (project_dir, project_dir_str) with NO flag file."""
    return tmp_path, str(tmp_path)


def _payload(
    *,
    session_id: str = SESSION_A,
    message: str = "",
    stop_hook_active: bool = False,
) -> dict:
    return {
        "session_id": session_id,
        "last_assistant_message": message,
        "stop_hook_active": stop_hook_active,
        "cwd": "/some/path",
    }


# ---------------------------------------------------------------------------
# Gate not armed (flag absent for this session) → always pass
# ---------------------------------------------------------------------------


def test_flag_absent_passes_even_with_bad_proposal(unarmed_dir):
    _, project_dir = unarmed_dir
    result = evaluate(_payload(message=BAD_MESSAGE_NO_EVIDENCE), project_dir)
    assert result is None


def test_flag_absent_passes_with_good_proposal(unarmed_dir):
    _, project_dir = unarmed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_STORY), project_dir)
    assert result is None


# ---------------------------------------------------------------------------
# Per-session isolation: flag for SESSION_A does NOT arm gate for SESSION_B
# ---------------------------------------------------------------------------


def test_per_session_isolation(armed_dir):
    """Flag for SESSION_A must not arm the gate when the payload carries SESSION_B."""
    _, project_dir = armed_dir
    result = evaluate(_payload(session_id=SESSION_B, message=BAD_MESSAGE_NO_EVIDENCE), project_dir)
    assert result is None


# ---------------------------------------------------------------------------
# Gate armed + valid evidence formats
# ---------------------------------------------------------------------------


def test_armed_story_citation_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_STORY), project_dir)
    assert result is None


def test_armed_metadata_citation_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_METADATA), project_dir)
    assert result is None


def test_armed_user_directed_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_USER_DIRECTED), project_dir)
    assert result is None


def test_armed_carry_forward_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_CARRY_FORWARD), project_dir)
    assert result is None


def test_armed_gap_found_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=GOOD_MESSAGE_GAP), project_dir)
    assert result is None


# ---------------------------------------------------------------------------
# Gate armed + bad proposals → block
# ---------------------------------------------------------------------------


def test_armed_missing_evidence_blocks(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=BAD_MESSAGE_NO_EVIDENCE), project_dir)
    assert result is not None
    assert result["decision"] == "block"
    assert "title" in result["reason"]


def test_armed_wrong_evidence_prefix_blocks(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=BAD_MESSAGE_WRONG_PREFIX), project_dir)
    assert result is not None
    assert result["decision"] == "block"
    assert "title" in result["reason"]


def test_armed_multi_block_all_good_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=MULTI_GOOD), project_dir)
    assert result is None


def test_armed_multi_block_one_bad_blocks(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=MULTI_BAD_SECOND), project_dir)
    assert result is not None
    assert result["decision"] == "block"
    # The second field "description" is missing evidence.
    assert "description" in result["reason"]


# ---------------------------------------------------------------------------
# No **Proposed Value:** in message → always pass (even when armed)
# ---------------------------------------------------------------------------


def test_armed_no_proposal_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=NO_PROPOSAL_MESSAGE), project_dir)
    assert result is None


def test_armed_empty_message_passes(armed_dir):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=""), project_dir)
    assert result is None


# ---------------------------------------------------------------------------
# stop_hook_active=True → never block (loop-safety)
# ---------------------------------------------------------------------------


def test_stop_hook_active_skips_block(armed_dir, capsys):
    _, project_dir = armed_dir
    result = evaluate(_payload(message=BAD_MESSAGE_NO_EVIDENCE, stop_hook_active=True), project_dir)
    assert result is None
    captured = capsys.readouterr()
    assert "stop_hook_active" in captured.err


# ---------------------------------------------------------------------------
# Malformed / missing session_id → no-op safely
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "not-a-uuid",
        "../../etc/passwd",
        "aaaaaaaa-aaaa-aaaa-aaaa",  # too short
        None,
    ],
)
def test_non_uuid_session_id_noop(armed_dir, bad_id):
    _, project_dir = armed_dir
    payload = {
        "session_id": bad_id,
        "last_assistant_message": BAD_MESSAGE_NO_EVIDENCE,
        "stop_hook_active": False,
    }
    result = evaluate(payload, project_dir)
    assert result is None


def test_missing_session_id_noop(armed_dir):
    _, project_dir = armed_dir
    payload = {
        "last_assistant_message": BAD_MESSAGE_NO_EVIDENCE,
        "stop_hook_active": False,
    }
    result = evaluate(payload, project_dir)
    assert result is None


# ---------------------------------------------------------------------------
# Missing / None project_dir → no-op
# ---------------------------------------------------------------------------


def test_none_project_dir_noop():
    result = evaluate(_payload(message=BAD_MESSAGE_NO_EVIDENCE), None)
    assert result is None


def test_empty_project_dir_noop():
    result = evaluate(_payload(message=BAD_MESSAGE_NO_EVIDENCE), "")
    assert result is None
