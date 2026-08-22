"""Fixture round-trip tests.

The canonical fixture must JSON-round-trip without loss and pass validate_world with zero errors.
If validate_world reports errors against the fixture, the validator is wrong and must be fixed.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent.parent / "example-world-schema-v2.4.json"
# Prior-version fixtures are retained for the back-compat tests below. v2.2 is the more
# load-bearing of the two: it is the only fixture carrying the pre-v2.4 bare-array shape
# for triggerPrereqs / triggerBlockers, so it is what proves the validator still reads
# worlds authored before the v2.4 gate-condition shape change.
FIXTURE_PATH_V22 = Path(__file__).parent.parent / "example-world-schema-v2.2.json"
FIXTURE_PATH_V21 = Path(__file__).parent.parent / "example-world-schema-v2.1.json"


@pytest.fixture
def fixture_world() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_fixture_file_exists():
    assert FIXTURE_PATH.exists(), "Canonical fixture file not found"


def test_fixture_valid_json(fixture_world):
    """Fixture must be parseable JSON."""
    assert isinstance(fixture_world, dict)


def test_fixture_round_trip(fixture_world):
    """Writing and re-reading the fixture must produce structurally identical data."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(fixture_world, f)
        tmp_path = f.name

    try:
        written = json.loads(Path(tmp_path).read_text())
        assert fixture_world == written, "Round-trip produced different data"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_fixture_passes_validator():
    """The canonical fixture must pass validate_world with zero errors.

    Per the design brief §3 rule 5: if the validator reports errors against the fixture,
    the validator is wrong and must be corrected.
    """
    from iw_architect.validator import validate_world

    result = json.loads(validate_world(str(FIXTURE_PATH)))
    assert result["errors"] == [], (
        "validate_world reported errors on the canonical fixture. "
        "The validator must be fixed:\n" + "\n".join(f"  - {e}" for e in result["errors"])
    )


def test_fixture_schema_version():
    """Fixture must have schemaVersion 2.4."""
    fixture = json.loads(FIXTURE_PATH.read_text())
    assert fixture["schemaVersion"] == 2.4


def test_v21_fixture_still_validates_clean():
    """Back-compat: the oldest retained fixture must still validate with NO errors.

    v2.1 worlds lack the v2.2 tracked-item fields (variableName, enforceFormat, …) and
    must remain valid — the new fields are all optional. The only surfaced findings are
    warnings (e.g. the 'schemaVersion 2.1 older than expected 2.4' notice, plus the
    XML-deprecation warning for the fixture's XML tracked item).
    """
    from iw_architect.validator import validate_world

    result = json.loads(validate_world(str(FIXTURE_PATH_V21)))
    assert result["errors"] == [], (
        "v2.1 fixture must still validate clean under the v2.4 validator:\n"
        + "\n".join(f"  - {e}" for e in result["errors"])
    )
    assert any("older" in w for w in result["warnings"]), result["warnings"]


def test_v22_fixture_still_validates_clean():
    """Back-compat: the v2.2 fixture must still validate with NO errors.

    v2.4 changed the `data` shape of triggerPrereqs / triggerBlockers from a bare array
    of trigger IDs to an object. Worlds authored before v2.4 carry the array, so the
    validator must keep reading it — degrading to a warning, never an error.
    """
    from iw_architect.validator import validate_world

    result = json.loads(validate_world(str(FIXTURE_PATH_V22)))
    assert result["errors"] == [], (
        "v2.2 fixture must still validate clean under the v2.4 validator:\n"
        + "\n".join(f"  - {e}" for e in result["errors"])
    )
    assert any("older" in w for w in result["warnings"]), result["warnings"]


def test_v22_fixture_legacy_gate_shape_still_cross_checked():
    """The pre-v2.4 bare-array gate shape must still resolve trigger IDs, and must warn.

    Scope note, because this is easy to misread: this test does **not** guard the silent-skip
    bug. The old ``isinstance(data, list)`` code handled *list*-shaped data correctly — that
    was never what broke. What broke was *dict*-shaped data falling through every branch. So
    the "unknown trigger id" assertion below cannot distinguish old code from new; under that
    mutation only the bare-array *warning* assertion fails.

    The tests that actually guard the silent skip are ``test_trigger_prereqs_unknown_id`` and
    ``test_trigger_blockers_unknown_id`` in ``test_validator.py``, which carry dict-shaped
    ``data``. If those payloads are ever weakened back to bare lists, this test will keep
    passing while the regression goes uncovered.
    """
    from iw_architect.validator import validate_world

    world = json.loads(FIXTURE_PATH_V22.read_text())
    for trigger in world["triggerEvents"]:
        for cond in trigger.get("triggerConditions", []):
            if cond.get("type") == "triggerPrereqs":
                cond["data"] = ["nosuchid"]

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(world, f)
        tmp = f.name
    try:
        result = json.loads(validate_world(tmp))
        assert any("triggerPrereqs references unknown trigger id" in e for e in result["errors"]), (
            "legacy bare-array triggerPrereqs must still be cross-checked; got errors: "
            f"{result['errors']}"
        )
        assert any("pre-v2.4 bare-array form" in w for w in result["warnings"]), result["warnings"]
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_fixture_pawscript_no_cross_reference_warnings():
    """The fixture's own effectRunScript (loop var $puppy + a real variableName) must
    produce zero PawScript cross-reference or read-only-native warnings."""
    from iw_architect.validator import validate_world

    result = json.loads(validate_world(str(FIXTURE_PATH)))
    assert not any("effectRunScript references" in w for w in result["warnings"]), result[
        "warnings"
    ]
    assert not any("read-only at runtime" in w for w in result["warnings"]), result["warnings"]


def test_scaffold_schema_version_is_2_4(tmp_path):
    """create_new_world_json must emit schemaVersion 2.4."""
    from iw_architect.tools.helpers import create_new_world_json

    output = tmp_path / "scaffold_version.json"
    create_new_world_json(str(output), title="Test World")
    world = json.loads(output.read_text())
    assert world["schemaVersion"] == 2.4


def test_scaffold_seeds_empty_conditions_registry(tmp_path):
    """schema v2.4: the scaffold seeds `conditions` so authors see the field exists."""
    from iw_architect.tools.helpers import create_new_world_json

    output = tmp_path / "scaffold_conditions.json"
    create_new_world_json(str(output), title="Test World")
    world = json.loads(output.read_text())
    assert world["conditions"] == []


def test_format_world_for_review_writes_file(tmp_path):
    """format_world_for_review writes a sibling .review.md file and returns its path."""
    from iw_architect.tools.inspection import _render_world_markdown, format_world_for_review

    # Copy the fixture into tmp_path so the sibling file lands in a writable dir
    world_copy = tmp_path / "world.json"
    world_copy.write_text(FIXTURE_PATH.read_text())

    result = json.loads(format_world_for_review(str(world_copy)))
    assert "success" in result, result
    assert "error" not in result
    review_path = Path(result["success"])
    assert review_path == world_copy.with_suffix(".review.md")
    assert review_path.exists()

    body = review_path.read_text()
    # Locks the file contents to the exact renderer output — guards against
    # silent truncation or formatter drift slipping past coarse heuristics.
    expected = _render_world_markdown(json.loads(world_copy.read_text()))
    assert body == expected
    assert "Enchanted Bake-Off" in body  # fixture title


def test_format_world_for_review_missing_file(tmp_path):
    """Missing file returns an error envelope, not a raised exception."""
    from iw_architect.tools.inspection import format_world_for_review

    result = json.loads(format_world_for_review(str(tmp_path / "nope.json")))
    assert "error" in result
    assert "success" not in result


def test_format_world_for_review_invalid_json(tmp_path):
    """Invalid JSON in the world file returns an error envelope."""
    from iw_architect.tools.inspection import format_world_for_review

    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    result = json.loads(format_world_for_review(str(bad)))
    assert "error" in result
    assert "success" not in result
    assert "Invalid JSON" in result["error"]


def test_scaffold_passes_validator(tmp_path):
    """create_new_world_json must produce a world that passes validate_world with zero errors."""
    from iw_architect.tools.helpers import create_new_world_json
    from iw_architect.validator import validate_world

    output = tmp_path / "scaffold_test.json"
    scaffold_result = json.loads(create_new_world_json(str(output), title="Test World"))
    assert scaffold_result["status"] == "created"

    validate_result = json.loads(validate_world(str(output)))
    assert validate_result["errors"] == [], (
        "create_new_world_json produced an invalid world:\n"
        + "\n".join(f"  - {e}" for e in validate_result["errors"])
    )


def test_scaffold_version_is_first_key(tmp_path):
    """`version` must be the first key a scaffolded world writes to disk.

    Key order is cosmetic to the platform, but the plugin deliberately surfaces
    `version` at the top so authors see it the moment they open the raw JSON. This
    guards that convention against an accidental reorder of _DEFAULT_SCAFFOLD.
    json.dumps serializes dict keys in insertion order, so the first key on disk is
    the first key of the scaffold dict.
    """
    from iw_architect.tools.helpers import create_new_world_json

    output = tmp_path / "scaffold_order.json"
    create_new_world_json(str(output), title="Test World")

    world = json.loads(output.read_text())
    assert next(iter(world)) == "version", (
        f"expected 'version' as the first key, got '{next(iter(world))}'"
    )


# ── make_draft_world tests ─────────────────────────────────────────────────────


def test_make_draft_world_copies_bumps_and_fronts_version(tmp_path):
    """Happy path: copy the fixture, bump `version`, surface it first, stay valid.

    Exercises the real fixture (where `version` sits second-to-last, before
    `designNotes`, with a trailing comma) — the common modify/spinoff case.
    """
    from iw_architect.tools.helpers import make_draft_world
    from iw_architect.validator import validate_world

    source = tmp_path / "world.json"
    source.write_text(FIXTURE_PATH.read_text())
    source_bytes_before = source.read_bytes()

    result = json.loads(make_draft_world(str(source)))
    assert result["status"] == "drafted", result
    draft = Path(result["draft_path"])
    assert draft == tmp_path / "world_draft.json"

    world = json.loads(draft.read_text())
    assert next(iter(world)) == "version", "version must be the first key in the draft"
    # Derive the expected bump from the fixture rather than hardcoding it: the fixture's
    # `version` moves whenever the platform export is refreshed, and this test is about
    # the bump-and-front behaviour, not the fixture's current number.
    source_version = json.loads(FIXTURE_PATH.read_text())["version"]
    major, minor = source_version.split(".")
    expected = f"{major}.{int(minor) + 1:0{len(minor)}d}"
    assert world["version"] == expected, f"fixture version {source_version} must bump to {expected}"
    assert result["version"] == {"from": source_version, "to": expected}

    # The source is the protected baseline: byte-for-byte unchanged.
    assert source.read_bytes() == source_bytes_before

    # The draft still validates clean.
    assert json.loads(validate_world(str(draft)))["errors"] == []


def test_make_draft_world_preserves_passthrough_fields(tmp_path):
    """Unknown platform-managed fields and every non-version value survive the draft."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    source.write_text(
        "{\n"
        '  "title": "T",\n'
        '  "schemaVersion": 2.1,\n'
        '  "futurePlatformField": {"nested": [1, 2, 3]},\n'
        '  "version": "1.04",\n'
        '  "designNotes": "keep me"\n'
        "}\n"
    )

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted", result

    draft = json.loads(Path(result["draft_path"]).read_text())
    assert next(iter(draft)) == "version"
    assert draft["version"] == "1.05"
    # Everything else is preserved verbatim, including the unknown field.
    assert draft["title"] == "T"
    assert draft["schemaVersion"] == 2.1
    assert draft["futurePlatformField"] == {"nested": [1, 2, 3]}
    assert draft["designNotes"] == "keep me"


def test_make_draft_world_handles_version_as_last_property(tmp_path):
    """When `version` is the last property (no trailing comma), the move must not

    leave a dangling comma on the new last property — json.loads succeeding proves it.
    """
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    source.write_text('{\n  "title": "T",\n  "schemaVersion": 2.1,\n  "version": "1.09"\n}\n')

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted", result

    draft = json.loads(Path(result["draft_path"]).read_text())  # would raise if comma broke
    assert next(iter(draft)) == "version"
    assert draft["version"] == "1.10"
    assert draft == {"version": "1.10", "title": "T", "schemaVersion": 2.1}


def test_make_draft_world_bumps_single_digit_minor_to_two_places(tmp_path):
    """`"1.3"` means 1.30 on the platform, so the draft must be 1.31 — not 1.4."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    source.write_text('{\n  "title": "T",\n  "version": "1.3"\n}\n')

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted", result
    assert result["version"] == {"from": "1.3", "to": "1.31"}
    assert json.loads(Path(result["draft_path"]).read_text())["version"] == "1.31"


def test_make_draft_world_handles_version_as_sole_property(tmp_path):
    """A degenerate world where `version` is the only key must still yield valid JSON.

    The relocated line must not carry a trailing comma when no other property follows it
    (`{"version": "1.05",}` would be invalid). Unreachable for a real IW world, but the
    surgery must never emit malformed output.
    """
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    source.write_text('{\n  "version": "1.04"\n}\n')

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted", result

    draft = json.loads(Path(result["draft_path"]).read_text())  # raises if comma broke it
    assert draft == {"version": "1.05"}


def test_make_draft_world_no_version_field_copies_unchanged(tmp_path):
    """A source without a `version` field is copied as-is; no key is injected."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    original = '{\n  "title": "T",\n  "schemaVersion": 2.1\n}\n'
    source.write_text(original)

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted"
    assert result["version"] is None

    draft = Path(result["draft_path"])
    assert json.loads(draft.read_text()) == {"title": "T", "schemaVersion": 2.1}
    assert "version" not in json.loads(draft.read_text())


def test_make_draft_world_derives_draft_path(tmp_path):
    """The default draft path appends `_draft` and increments a `_v<ver>` filename token."""
    from iw_architect.tools.helpers import make_draft_world

    cases = {
        "world.json": "world_draft.json",
        "world_v1.21.json": "world_v1.22_draft.json",
        "world_v2.09.json": "world_v2.10_draft.json",
        "world_v1.99.json": "world_v1.100_draft.json",
        "world_v1.3.json": "world_v1.31_draft.json",
    }
    for src_name, expected_draft in cases.items():
        source = tmp_path / src_name
        source.write_text('{\n  "version": "1.00",\n  "title": "T"\n}\n')
        result = json.loads(make_draft_world(str(source)))
        assert Path(result["draft_path"]).name == expected_draft, (
            f"{src_name} → {Path(result['draft_path']).name}, expected {expected_draft}"
        )


def test_make_draft_world_respects_explicit_dest(tmp_path):
    """An explicit draft_path (the spinoff flow) is used verbatim, not derived."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "origin.json"
    source.write_text('{\n  "version": "1.00",\n  "title": "T"\n}\n')
    dest = tmp_path / "my_variant.json"

    result = json.loads(make_draft_world(str(source), str(dest)))
    assert Path(result["draft_path"]) == dest
    assert dest.exists()
    assert json.loads(dest.read_text())["version"] == "1.01"


def test_make_draft_world_refuses_to_overwrite(tmp_path):
    """An existing destination is never clobbered — the tool errors instead."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "origin.json"
    source.write_text('{\n  "version": "1.00"\n}\n')
    dest = tmp_path / "taken.json"
    dest.write_text("DO NOT TOUCH")

    result = json.loads(make_draft_world(str(source), str(dest)))
    assert "error" in result
    assert "overwrite" in result["error"].lower()
    assert dest.read_text() == "DO NOT TOUCH"


def test_make_draft_world_rejects_relative_and_missing(tmp_path):
    """Relative paths and a non-existent source both return error envelopes."""
    from iw_architect.tools.helpers import make_draft_world

    assert "error" in json.loads(make_draft_world("relative/world.json"))
    missing = json.loads(make_draft_world(str(tmp_path / "nope.json")))
    assert "error" in missing
    assert "not found" in missing["error"].lower()


def test_make_draft_world_leaves_non_numeric_version_untouched(tmp_path):
    """A non-numeric trailing version component is copied as-is — not bumped or moved."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "w.json"
    source.write_text('{\n  "title": "T",\n  "version": "1.0-beta"\n}\n')

    result = json.loads(make_draft_world(str(source), str(tmp_path / "out.json")))
    assert result["status"] == "drafted"
    assert result["version"] == {"from": "1.0-beta", "to": "1.0-beta"}
    assert "non-numeric" in result["message"]

    draft = json.loads(Path(result["draft_path"]).read_text())
    assert draft["version"] == "1.0-beta"
    # Not moved to the top — title stays first since version couldn't be safely relocated.
    assert next(iter(draft)) == "title"


def test_make_draft_world_copies_invalid_json_and_reports(tmp_path):
    """Invalid-JSON source is still copied, but flagged — no surgery is attempted."""
    from iw_architect.tools.helpers import make_draft_world

    source = tmp_path / "bad.json"
    source.write_text("{not valid json")
    dest = tmp_path / "out.json"

    result = json.loads(make_draft_world(str(source), str(dest)))
    assert result["status"] == "copied"
    assert result["version"] is None
    assert "not valid json" in result["message"].lower()
    assert dest.read_text() == "{not valid json"


def test_bump_version_component():
    """Trailing-component increment preserves zero-pad width and handles carry."""
    from iw_architect.tools.helpers import _bump_version_component

    assert _bump_version_component("1.04") == "1.05"
    assert _bump_version_component("2.09") == "2.10"
    assert _bump_version_component("1.99") == "1.100"
    assert _bump_version_component("5") == "6"
    assert _bump_version_component("1.0-beta") is None  # non-numeric tail → left alone
    # IW versions are two-decimal-place numbers (1.09, 1.10, …). A single-digit minor is
    # how a trailing-zero version displays — "1.3" is 1.30 — so the bump must land on
    # 1.31, not 1.4 (which would skip nine versions).
    assert _bump_version_component("1.3") == "1.31"
    assert _bump_version_component("1.0") == "1.01"
    assert _bump_version_component("2.9") == "2.91"
    assert _bump_version_component("1.31") == "1.32"


def test_schema_coverage():
    """Walk the fixture and verify every top-level key is known to the schema model."""
    from iw_architect.schema_model import SCHEMA_SUMMARY

    fixture = json.loads(FIXTURE_PATH.read_text())
    known = set(SCHEMA_SUMMARY["topLevelFields"].keys())
    unknown = set(fixture.keys()) - known
    assert not unknown, (
        f"Fixture has top-level keys not in schema_model.SCHEMA_SUMMARY: {sorted(unknown)}"
    )


def _strictify(node):
    """Return a deep copy of a JSON Schema with extra-property restrictions injected.

    For every node that defines `properties`, add `additionalProperties: false` so the
    validator rejects unknown keys. For nodes that compose via `oneOf`/`anyOf`/`allOf`,
    use `unevaluatedProperties: false` instead — that keyword cooperates with composition
    by considering properties contributed by sub-schemas as "evaluated."

    A node may opt out of strictification by setting `x-iw-allow-extra-keys: true`; this
    is the escape hatch for objects intentionally left open to platform extensions.
    """
    if isinstance(node, list):
        return [_strictify(item) for item in node]
    if not isinstance(node, dict):
        return node

    out = {k: _strictify(v) for k, v in node.items()}

    if out.get("x-iw-allow-extra-keys"):
        return out

    has_properties = "properties" in out
    has_composition = any(k in out for k in ("oneOf", "anyOf", "allOf"))

    if has_properties and has_composition:
        out.setdefault("unevaluatedProperties", False)
    elif has_properties:
        out.setdefault("additionalProperties", False)

    return out


def test_strictify_helper_catches_unknown_keys():
    """Sanity check: _strictify must actually inject additionalProperties:false.

    Without this guard, test_fixture_schema_coverage_nested could be permanently
    green for the wrong reason — passing because _strictify failed to restrict,
    rather than because the fixture is genuinely covered.
    """
    import jsonschema

    from iw_architect.validator import _get_schema

    strict = _strictify(_get_schema())

    # Construct a minimal world with one NPC carrying an unknown field.
    minimal = {
        "schemaVersion": 2.1,
        "title": "Test",
        "NPCs": [
            {"id": "NPC000001", "name": "Test", "positionInList": 0, "moodColor": "blue"},
        ],
    }
    errors = [
        e
        for e in jsonschema.Draft202012Validator(strict).iter_errors(minimal)
        if e.validator in ("additionalProperties", "unevaluatedProperties")
    ]

    assert any("moodColor" in e.message for e in errors), (
        "_strictify did not inject additionalProperties:false where expected — "
        "test_fixture_schema_coverage_nested would be a false-green."
    )


def test_fixture_schema_coverage_nested(fixture_world):
    """Brief §6.2: every key at every depth in the fixture must be modeled in the schema.

    Uses jsonschema validation against a strictified copy of the schema. Any
    `additionalProperties`/`unevaluatedProperties` violation surfaces as a coverage gap —
    a fixture path the schema does not describe.

    The runtime validator does NOT use the strictified schema; per brief §3 rule 3
    (pass-through preservation) the runtime tolerates unknown fields. This test enforces
    completeness at build time only.
    """
    import jsonschema

    from iw_architect.validator import _get_schema

    strict_schema = _strictify(_get_schema())
    validator = jsonschema.Draft202012Validator(strict_schema)

    coverage_errors = [
        e
        for e in validator.iter_errors(fixture_world)
        if e.validator in ("additionalProperties", "unevaluatedProperties")
    ]

    paths = sorted(
        {f"{'.'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in coverage_errors}
    )

    assert not paths, (
        "Fixture has nested paths the JSON Schema does not model. "
        "Either add them to the schema or mark the parent with "
        "x-iw-allow-extra-keys: true.\n" + "\n".join(f"  - {p}" for p in paths)
    )


# ── mint_ids charset tests ─────────────────────────────────────────────────────

_ALNUM_RE = re.compile(r"^[A-Za-z0-9]+$")

_MINT_IDS_KINDS_AND_LENGTHS = [
    ("character", 8),
    ("npc", 9),
    ("trackedItem", 9),
    ("triggerEvent", 8),
    ("instructionBlock", 9),
    ("loreBookEntry", 9),
]


def test_mint_ids_alphanumeric_only():
    """mint_ids must emit only A-Za-z0-9 chars — no '+' or '/' (base64 extras).

    IW silently renames tracked-item IDs that contain '+' or '/' on import without
    updating trigger references, breaking trigger chains (confirmed June 2026).
    """
    import json

    from iw_architect.tools.helpers import mint_ids

    for kind, _ in _MINT_IDS_KINDS_AND_LENGTHS:
        result = json.loads(mint_ids(kind, 20))
        assert "ids" in result, f"mint_ids({kind!r}) returned error: {result}"
        for id_ in result["ids"]:
            assert _ALNUM_RE.match(id_), (
                f"mint_ids({kind!r}) emitted non-alphanumeric ID: {id_!r}. "
                "Base64 extras (+, /) must not appear in minted IDs."
            )


def test_mint_ids_expected_lengths():
    """mint_ids must preserve the expected per-entity-kind ID lengths."""
    import json

    from iw_architect.tools.helpers import mint_ids

    for kind, expected_len in _MINT_IDS_KINDS_AND_LENGTHS:
        result = json.loads(mint_ids(kind, 5))
        assert "ids" in result, f"mint_ids({kind!r}) returned error: {result}"
        for id_ in result["ids"]:
            assert len(id_) == expected_len, (
                f"mint_ids({kind!r}) returned ID of length {len(id_)}, "
                f"expected {expected_len}: {id_!r}"
            )
