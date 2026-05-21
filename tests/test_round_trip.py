"""Fixture round-trip tests.

The canonical fixture must JSON-round-trip without loss and pass validate_world with zero errors.
If validate_world reports errors against the fixture, the validator is wrong and must be fixed.
"""

from __future__ import annotations

import json
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


def test_format_world_for_review_runs(tmp_path):
    """format_world_for_review must return a non-empty string for the fixture."""
    from iw_architect.tools.inspection import format_world_for_review

    result = format_world_for_review(str(FIXTURE_PATH))
    assert isinstance(result, str)
    assert "Enchanted Bake-Off" in result  # fixture title
    assert len(result) > 500


def test_scaffold_passes_validator(tmp_path):
    """scaffold_world must produce a world that passes validate_world with zero errors."""
    from iw_architect.tools.helpers import scaffold_world
    from iw_architect.validator import validate_world

    output = tmp_path / "scaffold_test.json"
    scaffold_result = json.loads(scaffold_world(str(output), title="Test World"))
    assert scaffold_result["status"] == "created"

    validate_result = json.loads(validate_world(str(output)))
    assert validate_result["errors"] == [], (
        "scaffold_world produced an invalid world:\n"
        + "\n".join(f"  - {e}" for e in validate_result["errors"])
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
