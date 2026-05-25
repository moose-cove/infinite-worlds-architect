# Infinite Worlds Architect

Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds.

## Project structure

```
src/iw_architect/
├── server.py          # MCP server entry point (FastMCP, stdio transport)
├── validator.py       # Two-tier world validator (jsonschema + custom checks)
├── schema_model.py    # Deriver: builds SCHEMA_SUMMARY from the JSON Schema at import time
└── tools/
    ├── inspection.py  # read_world_field, format_world_for_review, get_schema_summary
    ├── helpers.py     # scaffold_world, mint_ids, confirm_path
    └── analysis.py    # audit_world, compare_worlds, get_diff_summary

tests/
├── test_round_trip.py  # Fixture round-trip + scaffold tests (most critical)
├── test_validator.py   # Negative tests for every error class in §4.6
└── test_analysis.py    # Tests for audit_world, compare_worlds, get_diff_summary

skills/
└── world-architect/                                 # Top-level discovery skill (model-invoked)
    └── references/
        ├── WORLD_JSON_SCHEMA_v2.1.md                # Human-readable schema reference
        └── world_v2.1.schema.json                   # JSON Schema artifact (Tier 1 validator)

commands/
├── new-world/          # /infinite-worlds-architect:new-world  — guided world creation
├── modify-world/       # /infinite-worlds-architect:modify-world — edit existing world
└── spinoff-world/      # /infinite-worlds-architect:spinoff-world — derive a variant

.claude-plugin/
├── plugin.json         # Plugin manifest
└── marketplace.json    # Marketplace index entry

.github/workflows/ci.yml   # GitHub Actions: tests + version-bump check
.mcp.json                  # MCP server spawn configuration
```

## Setup

```bash
uv sync --all-extras              # creates .venv/ and installs runtime + dev deps
uv run pre-commit install         # registers the git pre-commit hook
uv run pytest
```

`uv sync` resolves against `pyproject.toml` (PEP 621 metadata + `[project.optional-dependencies].dev`) and writes the environment to `./.venv/`. The pre-commit config's hook entries reference `.venv/bin/ruff` and `.venv/bin/pytest` directly, so they pick up the same binaries `uv sync` installed — no extra wiring needed.

Prefer `uv run <cmd>` over activating the venv. It avoids stale `$PATH` state across worktrees and is what CI runs.

<details>
<summary>Legacy pip/venv setup (still works, no longer the default)</summary>

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pre-commit install
.venv/bin/pytest
```

</details>

### Setting up a new worktree

When you create a worktree via `EnterWorktree` (or `claude --worktree <name>`), it lands at `.claude/worktrees/<name>/` with the git history but **no `.venv/`** — venvs are per-working-directory, not shared across worktrees. Bootstrap inside the worktree:

```bash
uv sync --all-extras              # creates .venv/ in this worktree
uv run pytest                     # sanity-check the install
```

The repo's pre-commit hooks are installed in the main repo's `.git/hooks/` and fire for every worktree, but their entries are relative paths (`.venv/bin/ruff` etc.). That's why each worktree needs its own `.venv/` — without it, `git commit` inside the worktree will fail with "ruff: not found". `uv sync` is the one-shot fix.

## Pre-commit hook policy

`.pre-commit-config.yaml` mirrors the GitHub Actions CI workflow exactly: every check that fails in CI will fail on commit, locally, with the same arguments. This is intentional — it shortens the feedback loop from "wait for CI" to "wait for `git commit`".

**Never bypass the pre-commit hook.** Do not run `git commit --no-verify`, do not set `SKIP=...`, do not edit `.pre-commit-config.yaml` to silence checks rather than fix them, and do not delete `.git/hooks/pre-commit`. If the hook is failing, fix the underlying issue — the failure is the system working as designed.

The only legitimate reason to change the hook config is to keep it in sync with `.github/workflows/ci.yml` when CI changes; the two must stay aligned.

## Running the MCP server

```bash
uv run python -m iw_architect.server
```

(`.venv/bin/python -m iw_architect.server` also works once the venv is built.)

## Source-of-truth rules (from DESIGN_BRIEF_v2.md §3)

1. **`example-world-schema-v2.1.json` is the schema.** If `validate_world` reports errors on the fixture, the validator is wrong — fix the validator to accept the fixture.
2. **Read before writing.** Always call `Read` on the JSON before any `Edit`.
3. **Pass-through preservation.** Unknown fields survive because the agent edits in place.
4. **`schemaVersion` is load-bearing.** Read and write it on every world.
5. **The validator enforces; the schema doc explains; the fixture is ground truth.**

## Design constraints

- **No write tools.** The plugin has no add/modify/remove MCP tools. The agent edits `world.json` directly with Claude Code's native `Read`, `Edit`, `Write` tools.
- **Single source of schema truth.** `skills/world-architect/references/world_v2.1.schema.json` is the canonical schema artifact. `validator.py` enforces it (Tier 1 jsonschema + Tier 2 custom checks). `schema_model.py` derives `SCHEMA_SUMMARY` from it at import time for the LLM-facing summary. When the platform schema evolves, edit the JSON Schema — the rest follows.
- **Warn, don't error** on unknown top-level keys, unknown effect types, and future schema versions — the platform may add fields the validator doesn't know about. Build-time strictness is enforced separately by `test_fixture_schema_coverage_nested` in `tests/test_round_trip.py`.

## Adding a new platform feature

The JSON Schema is the single edit point — `SCHEMA_SUMMARY` derives from it automatically, so there is no second place to update.

1. **Edit the JSON Schema** at `skills/world-architect/references/world_v2.1.schema.json`:
   - For a new top-level field: add an entry to `properties` with `description`, `x-iw-category`, optionally `default`, `x-iw-note`, `enum`.
   - For a new entity field: add it under the relevant `$defs.<entity>.properties`. If required, also add the field name to that `$defs.<entity>.required` array.
   - For a new effect/condition type: add an entry to `$defs.triggerEffect.x-iw-effect-types` or `$defs.triggerCondition.x-iw-condition-types`. Register the type in `validator.py`'s `_KNOWN_EFFECT_TYPES` / `_KNOWN_CONDITION_TYPES` set so it stops warning as "unknown".
2. **Add cross-reference checks** to `validator.py` if the new field references other entity IDs (e.g. tracked-item, instruction-block, trigger IDs).
3. **Add a negative test** in `tests/test_validator.py` that constructs a world violating the new rule and asserts `validate_world` reports it.
4. **Run `uv run pytest`.** The fixture round-trip (§6.1) and nested coverage tests (§6.2) will catch any drift between the schema and the canonical fixture.

`schema_model.SCHEMA_SUMMARY` and `get_schema_summary()` update automatically — no manual edit needed.

## Open questions (from DESIGN_BRIEF_v2.md §9)

- `illustrationStyle*HighPriority` / `LowPriority` coexistence rules with older `imageStyle*` fields
- `recommendedAIModel` full enum of valid values (fixture only shows `null`)

These are preserved verbatim and not validated beyond type-checking until a fixture clarifies them.

## Python version

3.12.13 (pinned in `.tool-versions`)

## Tools and libraries

| Tool | Purpose |
|---|---|
| `asdf` | Python version selection (`.tool-versions` pins 3.12.13) |
| `uv` | Package and environment management (`uv sync --all-extras`, `uv run …`); creates the project's `.venv/` |
| `mcp` | Official Python MCP SDK (FastMCP, stdio transport) |
| `jsonschema` | Tier 1 structural validation |
| `ruff` | Linting and formatting |
| `pytest` + `pytest-cov` | Testing (80% coverage threshold) |
| `pre-commit` | Pre-commit hooks (lint + tests) |
