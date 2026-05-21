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
        f"The validator must be fixed:\n"
        + "\n".join(f"  - {e}" for e in result["errors"])
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
