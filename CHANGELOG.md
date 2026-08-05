# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Per the project's versioning policy, `.claude-plugin/plugin.json`, `pyproject.toml`,
and `.claude-plugin/marketplace.json` always carry the same version, bumped in
lockstep with the change that warrants it.

## [Unreleased]

### Changed

- **World schema v2.2 → v2.4.** The canonical fixture is now `example-world-schema-v2.4.json`; the schema artifact and human-readable reference are renamed to `references/world_v2.4.schema.json` and `references/WORLD_JSON_SCHEMA_v2.4.md` (root symlink repointed), and `KNOWN_SCHEMA_VERSION` / the `create_new_world_json` scaffold now emit `schemaVersion: 2.4`. Three substantive deltas:
  - **`triggerPrereqs.data` and `triggerBlockers.data` changed shape** — from a bare `string[]` of trigger IDs to `{prereqs|blockers: string[], firedThisTurn: boolean}`. The validator reads **both** forms so pre-v2.4 worlds keep validating (warning, never error), and cross-reference checking now runs against either. This mattered: the previous code matched on `isinstance(data, list)`, so a v2.4 world would have silently skipped dangling-trigger-ID detection entirely rather than failing loudly. `firedThisTurn` is type-checked but its semantics are documented as an **open question** — the fixture only ever shows `false`, so that is what the plugin emits and recommends.
  - **New top-level `conditions: string[]`** — the named-event registry that backs `triggerOnEvent`. Declaring an event there is what makes it selectable in the world editor's trigger UI. New validator check warns (never errors) when a `triggerOnEvent` string is not declared, recursing into `category: "logic"` combinators; the scaffold seeds an empty `conditions` array.
  - `audit_world`'s prerequisite-cycle detector reads both gate-condition shapes, so cycle detection no longer goes blind on v2.4 worlds.
  - Two further `conditions` checks: a warning on a declared event no `triggerOnEvent` uses (the reverse of the undeclared-event warning), and a warning past the documented cap of 10 AI-evaluated events per world. The cap is wiki-corroborated rather than fixture-proven, so it is deliberately a warning and deliberately not encoded as `maxItems` in the JSON Schema.
  (`example-world-schema-v2.4.json`, `references/world_v2.4.schema.json`, `references/WORLD_JSON_SCHEMA_v2.4.md`, `src/iw_architect/__init__.py`, `src/iw_architect/validator.py`, `src/iw_architect/schema_model.py`, `src/iw_architect/tools/helpers.py`, `src/iw_architect/tools/analysis.py`)

- **Documented that YAML tracked items support the entire YAML language, at any depth.** Nothing about `dataType: "yaml"` was ever restricted to flat keys, but every example in the reference material was flat — and at least one authoring session concluded from the examples that nesting was unsupported. The canonical fixture's puppy tracker now nests (`friendliness` / `energy` moved under a `stats:` sub-map, with `formatSchema`, `formatExample`, `initialValue`, and the `effectRunScript` body updated to `$puppy.stats.friendliness`), and `references/fields/YAML_TRACKED_ITEMS.md` gains an explicit "the whole YAML language is supported" section mapping every construct in <https://infiniteworlds.app/yaml-guide> — nesting, lists inside things, empty lists, block scalars (`|` / `>`), comments, quoting. `references/mechanics/PAWSCRIPT.md` documents dot-chained nested path access and assignment; `agents/world-architect.md` gains an explicit "never tell an author nesting is unsupported" rule. (`example-world-schema-v2.4.json`, `references/fields/YAML_TRACKED_ITEMS.md`, `references/fields/TRIGGER_EVENTS.md`, `references/mechanics/PAWSCRIPT.md`, `references/WORLD_JSON_SCHEMA_v2.4.md`, `agents/world-architect.md`, `commands/new-world.md`, `commands/modify-world.md`)

- **`example-world-schema-v2.2.json` is now a load-bearing back-compat fixture.** It is the only fixture carrying the pre-v2.4 bare-array gate shape, so it is what proves the validator still reads worlds authored before the change. `example-world-schema-v2.1.json` is retained as before. Both must still validate with warnings only. (`tests/test_round_trip.py`)

### Fixed

- **Nine Tier 2 checks crashed on a non-object entry in an entity array.** `"trackedItems": ["oops"]` made every check that calls `.get()` on those members raise. Rather than nine near-identical isinstance gates — one of which the tenth check would inevitably forget — `_sanitize_entity_arrays` drops malformed entries once, before Tier 2 runs, and records why semantic coverage is incomplete. Tier 1 has already reported each entry as a structural type error, so dropping loses nothing. Nested `triggerConditions` / `triggerEffects` are cleaned the same way. Found by tightening a test that had been passing for the wrong reason. (`src/iw_architect/validator.py`)

- **Every guard added in this PR is now mutation-tested.** A review pass established that all four originally-added guards left the suite green when deleted — tests that assert "a report came back" cannot distinguish a leaf guard from the catch-all wrapper underneath it, and one test passed only because its fixture placeholder string (`"not an object"`) happened to appear in an unrelated jsonschema message. The tests now pin mechanisms rather than outcomes: the `conditions` guard is verified by asserting the backstop message is *absent*, the two depth caps by asserting the walk actually truncates, both `except` arms of the Tier 2 wrapper by monkeypatching a check to raise. Verified by removing each of the six guard sites in turn on a scratch copy and confirming the suite fails each time. (`tests/test_validator.py`)

- **`validate_world` could raise instead of returning a report.** It is an MCP tool documented to always return JSON with `valid` / `errors` / `warnings`, but two inputs broke that contract. A world carrying an explicit `"conditions": null` (or any non-list) hit `world.get("conditions", [])` — which only defaults when the key is *absent* — and raised `TypeError` out of the tool; a bare-string value was quietly worse, iterating the string's characters into the declared-event set. Separately, deeply nested `category: "logic"` condition trees exhausted the Python stack in three recursive walkers. Now: `conditions` is type-guarded, condition walks stop at `_MAX_CONDITION_DEPTH`, `json.loads` handles `RecursionError`, and the whole Tier 2 pass is wrapped so an unanticipated shape degrades to a reported error rather than a traceback. `_check_duplicate_ids` also no longer crashes on a non-dict entity entry — it ran first, so its crash pre-empted every downstream `isinstance` guard and made them unreachable on real malformed input. (`src/iw_architect/validator.py`, `tests/test_validator.py`)

- **Two platform claims were stated as fact on no evidence.** "The platform migrates the pre-v2.4 bare array on import" was an assumption, and it underwrote advice in the risky direction — `TRIGGER_EVENTS.md` concluded that leaving a legacy gate condition unmigrated was fine, which holds only if the migration happens. If it doesn't, the gate silently stops gating and the trigger over-fires with no error anywhere. Now documented as unverified, with the advice flipped to "migrate it while you're in that world." Likewise, the `conditions` registry's *mechanism* (that declaring an event is what makes it selectable in the editor's trigger UI) was asserted in eight places including a user-facing validator warning; exact-text keying is well-supported by the fixture, but the mechanism is not, and a competing reading — that the platform derives `conditions` from the events already in use, which would also explain how the ten-event cap is enforced — fits the same evidence. Both readings are now documented, along with the round-trip experiment that would settle them. The authoring instruction is unchanged, because it is identical either way. (`references/`, `agents/world-architect.md`, `src/iw_architect/validator.py`, `src/iw_architect/tools/helpers.py`)

- **`agents/world-architect.md` could not call four of the MCP tools its own body instructs it to use.** The frontmatter `tools:` list is a whitelist, and `make_draft_world` was missing from it — while the agent body makes that tool the mandatory first action of every modify flow, guarding its central safety property ("never edit the file the author handed you"). The three story-export tools that `/sequel-world` drives (`extract_story_data`, `query_story_data`, `get_character_list`) were missing for the same reason. All four added, plus `tests/test_agent_tool_allowlist.py` to catch the drift class in both directions: a tool named in the body but absent from the allowlist, and an allowlisted tool the server no longer registers. (`agents/world-architect.md`, `tests/test_agent_tool_allowlist.py`)

- **Two dead documentation paths in the project reviewer agent.** `tools/helpers.py` did not resolve from any root (it is `src/iw_architect/tools/helpers.py`), and a whole review-criteria section was still addressed to `skills/world-architect/SKILL.md`, removed back in f137372 when the skill was replaced by the `world-architect` agent. The section is retargeted at the agent, and gains a tool-allowlist-coverage criterion. Both were found by widening `tests/test_doc_links.py`'s `_DOC_GLOBS` to cover `.claude/agents/**/*.md` and `.github/*.md` — directories that carry schema-artifact paths (11 references and 3 respectively) but were unprotected, which is exactly the "breakage hides in files the change didn't otherwise touch" class that module exists to catch. (`.claude/agents/iw-architect-reviewer.md`, `tests/test_doc_links.py`)

- **Stale current-version claims across the reference tree.** The rename ripple updated *filenames* but not *prose*: both plugin manifests advertised "Validates world JSON against the v2.2 schema" (now version-agnostic, so it cannot go stale again), and nine reference-doc passages still asserted v2.2 as the current version — several while linking to `WORLD_JSON_SCHEMA_v2.4.md` in the same sentence. Provenance notes ("New in v2.2", "deprecated as of v2.2") are correct and were deliberately left alone. Separately, `references/fields/TRACKED_ITEMS.md` listed a five-value `visibility` enum against the schema's six — `hidden_boring` was missing. (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `references/`)

### Added

- **`/infinite-worlds-architect:sequel-world` command.** Builds a sequel world from an original world JSON plus one or more played story-export `.txt` files: copies the source untouched, extracts the story (`extract_story_data` / `query_story_data` / `get_character_list`), then walks the author field-by-field, proposing each evolved value with cited evidence. Ships with an optional, consent-armed **citation gate** (`hooks/citation_gate.py`, the plugin's first `Stop` hook) that enforces an evidence line on every field proposal, and a general `references/mechanics/STORY_EXPORT_EXTRACTION_GUIDE.md` covering the story-extraction tools for any flow (e.g. a `modify-world` agent inspecting an export). (`commands/sequel-world.md`, `hooks/`, `references/`)

## [0.7.1] - 2026-06-03

### Fixed

- **Path-taking MCP tools now reject relative paths with an actionable error instead of silently resolving them against the wrong directory.** The MCP server runs as a separate process whose working directory is not the agent's session directory, so `Path(...).resolve()` on a relative path produced a bogus absolute path and a confusing "file/parent does not exist" error. A shared guard (`src/iw_architect/paths.py`) now requires an absolute path (a leading `~` is still expanded) across `confirm_path`, `validate_world`, `read_world_field`, `format_world_for_review`, `audit_world`, `compare_worlds`, `get_diff_summary`, and `create_new_world_json`; the error names the server's working directory and tells the caller to resolve to absolute first. The `new-world`, `modify-world`, and `spinoff-world` commands and the `world-architect` agent now instruct the agent to resolve paths to absolute (`realpath -m`) before calling these tools. (`src/iw_architect/paths.py`, `src/iw_architect/tools/helpers.py`, `src/iw_architect/tools/inspection.py`, `src/iw_architect/tools/analysis.py`, `src/iw_architect/validator.py`, `commands/*.md`, `agents/world-architect.md`)

## [0.7.0] - 2026-06-02

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
