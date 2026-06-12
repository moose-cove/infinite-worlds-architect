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

FIXTURE_PATH = Path(__file__).parent.parent / "example-world-schema-v2.1.json"


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
    """Fixture must have schemaVersion 2.1."""
    fixture = json.loads(FIXTURE_PATH.read_text())
    assert fixture["schemaVersion"] == 2.1


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
