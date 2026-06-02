# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Per the project's versioning policy, `.claude-plugin/plugin.json`, `pyproject.toml`,
and `.claude-plugin/marketplace.json` always carry the same version, bumped in
lockstep with the change that warrants it.

## [Unreleased]

## [1.0.0] - 2026-06-02

### Changed

- **`scaffold_world` renamed to `create_new_world_json`.** The MCP tool surface now uses a name that makes its intent unambiguous without context. All internal references, tests, commands, and documentation updated. (`src/iw_architect/tools/helpers.py`, `src/iw_architect/server.py`)

## [0.6.0] - 2026-05-30

### Added

- **`validate_world` warns when `imageStyle` is null.** Null `imageStyle` is
  tolerated (the schema now permits `["string", "null"]` for that one field) but
  discouraged; the Tier 2 warning recommends a preset such as `"photo_1"`. The nine
  sibling image fields (`imageModel`, `imageStyle*Pre/Post`, `illustrationStyle*`)
  stay string-only, so a null there remains a Tier 1 error and `""` is the correct
  "unset" value. (`src/iw_architect/validator.py`, `references/world_v2.1.schema.json`)

### Changed

- **`create_new_world_json` seeds richer image-prompt defaults.** `imageStyleCharacterPre`,
  `imageStyleCharacterPost`, and `imageStyleNonCharacterPre` now carry sensible
  default prompt text instead of empty strings (`imageModel: "manticore"`,
  `imageStyle: "photo_1"` unchanged). (`src/iw_architect/tools/helpers.py`)
- **`world-architect` edit-flow contract forbids parallel edits to the same world
  JSON.** Concurrent `Edit`/`Write` calls on one file fail with "File has not been
  read yet" and silently lose changes; edits must be sequential. Added edge-case
  guidance to seed the image-field defaults on import (when fields are null/missing
  and the author hasn't set their own) and against using inline-Bash Python
  (heredoc escaping) for JSON surgery. (`agents/world-architect.md`)
- **`/modify-world` trigger-minting guidance clarified.** `mint_ids("triggerStep", n)`
  needs one distinct UUID per condition *and* per effect; `format_world_for_review`
  is now scoped to session start/end with `read_world_field` for mid-session
  inspection. `/spinoff-world` copies via `Read` + `Write` only. (`commands/`)

### Fixed

- **`.claude-plugin/marketplace.json` version drift.** It had silently fallen to
  `0.3.0` while `plugin.json` / `pyproject.toml` advanced, because the CI
  version-bump job never checked it. The job now asserts all three manifests are
  bumped and equal, and the marketplace version is realigned. (`.github/workflows/ci.yml`)
- **Broken `WORLD_JSON_SCHEMA_v2.1.md` root symlink** repointed at
  `references/WORLD_JSON_SCHEMA_v2.1.md` (it dangled at a non-existent `skills/`
  path, breaking the agent's Tier 3 schema reference).

### Tests

- Added tests asserting null `imageStyle` warns but validates clean, and null
  `imageModel` is a Tier 1 error. Suite: 85 tests.

## [0.5.1] - 2026-05-29

### Fixed

- **`compare_worlds` / `get_diff_summary` no longer silently drop id-less entities.**
  When an entity array's representative element had an `id`, the whole list was
  keyed by `id` and any entity lacking that key was excluded from both sides of
  the diff — so adding or removing such an entity produced zero changes. Unkeyed
  entities are now compared positionally (and re-keyed by `name` when present)
  so every change surfaces. Set-union sort is now `key=str`-safe against mixed
  key types. (`src/iw_architect/tools/analysis.py`)

### Changed

- **`create_new_world_json` deep-copies its default template.** The scaffold previously
  used a shallow `dict()` copy, leaving nested containers (lists, the
  `permissionsOnceShared` dict) aliased to the module-level constant. Switched to
  `copy.deepcopy` to honor the project's immutability rule and remove the
  footgun. No observable behavior change today. (`src/iw_architect/tools/helpers.py`)
- **`audit_world` per-character override check simplified.** Collapsed redundant
  per-iteration recomputation of the tracked-item id set and an O(missing × items)
  name lookup into a single precomputed id→name map. Behavior is unchanged;
  existing tests guard it. (`src/iw_architect/tools/analysis.py`)

### Tests

- Added regression tests for the diff-fidelity fix (`compare_worlds` and
  `get_diff_summary` with an id-less entity) and a positive-case lock for the
  per-character override audit. Suite: 83 tests, 87% coverage.

## [0.5.0] and earlier

Detailed per-version history before `0.5.1` predates this changelog. Highlights,
reconstructable from `git log`:

- **0.5.0** — `format_world_for_review` writes the rendered Markdown to a sibling
  `.review.md` file instead of returning it inline, keeping the calling agent's
  context clean.
- **0.3.0** — CI enforcement of `plugin.json` / `pyproject.toml` version lockstep
  plus a PR template; `world-architect` agent and `iw-architect-reviewer` review
  agent added; world-architect skill replaced with agent-loaded references.
- **0.1.0** — initial plugin: FastMCP stdio server, two-tier validator
  (`jsonschema` + custom semantic checks), `SCHEMA_SUMMARY` derived from the v2.1
  JSON Schema, inspection/helper/analysis tools, and the
  `new-world` / `modify-world` / `spinoff-world` commands.

For exact commit-level history, see `git log`.

[Unreleased]: https://github.com/moose-cove/infinite-worlds-architect/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/moose-cove/infinite-worlds-architect/compare/v0.5.0...v0.5.1
