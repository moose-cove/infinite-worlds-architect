# Infinite Worlds Architect

Claude Code plugin for building and editing [Infinite Worlds](https://infiniteworlds.app) story worlds.

## Worktree & branch discipline (read first)

**Default to working in a git worktree on a feature branch. Never make edits in the primary
working directory or directly on `main` unless the user explicitly instructs you to.**

Before making *any* change to this repository:

1. Create and enter a worktree with the `EnterWorktree` tool (it branches from `origin/HEAD`
   onto a new `worktree-<name>` branch and switches the session into it). Do **not** hand-roll
   this with `git worktree add` — see the global worktree rules.
2. Make your edits, commit them on that branch, and open a PR from it.
3. Leave the worktree with `ExitWorktree` when done.

The only times it is acceptable to edit the primary checkout / `main` directly are when the
user says so in plain terms (e.g. "just edit it in place", "commit straight to main", "don't
bother with a worktree"). Approval for one change does not carry over to the next — if in
doubt, branch.

This protects `main` as a always-shippable, last-known-good state and keeps every change
reviewable in isolation.

## Project structure

```
src/iw_architect/
├── server.py          # MCP server entry point (FastMCP, stdio transport)
├── validator.py       # Two-tier world validator (jsonschema + custom checks)
├── schema_model.py    # Deriver: builds SCHEMA_SUMMARY from the JSON Schema at import time
└── tools/
    ├── inspection.py  # read_world_field, format_world_for_review, get_schema_summary
    ├── helpers.py     # create_new_world_json, make_draft_world, mint_ids, confirm_path
    └── analysis.py    # audit_world, compare_worlds, get_diff_summary

tests/
├── test_round_trip.py  # Fixture round-trip + scaffold tests (most critical)
├── test_validator.py   # Negative tests for every error class in §4.6
└── test_analysis.py    # Tests for audit_world, compare_worlds, get_diff_summary

references/                                          # On-demand authoring + schema references
├── README.md                                        # Index, authoring-intent lookup, ID-format table
├── WORLD_JSON_SCHEMA_v2.4.md                        # Human-readable schema reference
├── world_v2.4.schema.json                           # JSON Schema artifact (Tier 1 validator)
├── mechanics/                                       # Runtime and platform behaviour
│   ├── AI_RUNTIME_MECHANICS.md                      # Runtime/turn-lifecycle behavior
│   ├── PAWSCRIPT.md                                 # PawScript expressions + scripts (effectRunScript)
│   ├── PLATFORM_BEHAVIOR_NOTES.md                  # Import, ID renaming, World Debug, Export
│   └── STORY_EXPORT_EXTRACTION_GUIDE.md             # Using the story-export extraction tools (any agent)
├── guidance/                                        # Authoring principles
│   ├── FIELD_ALLOCATION_STRATEGY.md                 # Where content belongs
│   ├── CHARACTER_AUTHORING_GUARDRAILS.md            # No-fabrication discipline
│   └── LAYERED_KNOWLEDGE_ISOLATION.md              # NPC knowledge isolation patterns
├── fields/                                          # Per-field authoring judgment notes
│   └── *.md                                         # INTRODUCING_THE_STORY, TRIGGER_EVENTS, YAML_TRACKED_ITEMS, etc.
├── patterns/                                        # Reusable design patterns
│   └── *.md                                         # PHASE_ESCALATION, SURVIVAL_STATS, etc.
└── templates/                                       # Ready-to-use EIB content
    └── *.md                                         # AI_TAMING, CLAUDE_TAMING, etc.

agents/
└── world-architect.md                               # Autonomous + command-loaded agent

commands/
├── new-world.md        # /infinite-worlds-architect:new-world  — guided world creation
├── modify-world.md     # /infinite-worlds-architect:modify-world — edit existing world
├── spinoff-world.md    # /infinite-worlds-architect:spinoff-world — derive a variant
└── sequel-world.md     # /infinite-worlds-architect:sequel-world — build a sequel from story export(s)

hooks/
├── citation_gate.py    # Stop hook: enforces evidence citations during a sequel-world flow
└── hooks.json          # Hook registration (Stop → citation_gate.py)

probes/                     # Instrument worlds for resolving documented schema unknowns
├── README.md               # Run + read protocol; recorded results; where findings land
├── probe-a-core.json       # Gate shapes, firedThisTurn, conditions registry, YAML, image style
├── probe-a-imported.json   # Probe A after an IW import/export round trip — evidence, do not edit
├── probe-b-cap.json        # Ten-event cap, recommendedAIModel, Probe A factor-isolation follow-ups
├── probe-b-imported.json   # Probe B after an IW import/export round trip — evidence, do not edit
├── probe-d-pawscript-runtime.md    # Probe D build spec (trigger firing + PawScript runtime cells)
├── probe-d-pawscript-runtime.json  # Probe D world as built
├── probe-d-imported.json           # Probe D after import/export — evidence, do not edit
└── harness/                # Playwright/CDP scripts that import, export and play probes against live IW

.claude-plugin/
├── plugin.json         # Plugin manifest (includes inline `mcpServers` config for the iw-json-tools stdio server)
└── marketplace.json    # Marketplace index entry

.github/workflows/ci.yml   # GitHub Actions: tests + version-bump check
```

## Setup

```bash
uv sync --all-extras              # creates .venv/ and installs runtime + dev deps
uv run pre-commit install         # registers the git pre-commit hook
uv run pytest
```

`uv sync` resolves against `pyproject.toml` (PEP 621 metadata + `[project.optional-dependencies].dev`) and writes the environment to `./.venv/`. The pre-commit config's hook entries reference `.venv/bin/ruff` and `.venv/bin/pytest` directly, so they pick up the same binaries `uv sync` installed — no extra wiring needed.

Prefer `uv run <cmd>` over activating the venv. It avoids stale `$PATH` state across worktrees and is what CI runs.

### Lockfile policy

`uv.lock` is committed and is the source of truth for which dependency versions CI installs. Rules:

- **Never edit `uv.lock` by hand.** It's regenerated by uv.
- **Adding or removing a dependency:** run `uv add <pkg>` / `uv remove <pkg>` — both update `pyproject.toml` and `uv.lock` atomically. Commit both files in the same change.
- **Editing `pyproject.toml` dependencies manually:** run `uv lock` afterwards to refresh `uv.lock`. Commit both files together.
- **Upgrading versions:** `uv lock --upgrade` (all) or `uv lock --upgrade-package <pkg>` (one). This is the only time `uv.lock` should change without a `pyproject.toml` change.
- **CI runs `uv sync --all-extras --locked`** so any drift between `pyproject.toml` and `uv.lock` fails the build instead of silently re-resolving. Locally, you can check for drift with `uv lock --check`.

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

### Dispatching an agent into a worktree

When a subagent is going to implement a plan that lives in `claude-scratchpad/`, include the plan content **inline in the agent's prompt** rather than referencing the file path. Two reasons: (1) `claude-scratchpad/` is gitignored, so plan files do not appear in the worktree's checkout; (2) if the worktree's branch base predates a recent merge into the target branch, the agent will work from a stale view of the plan and may redo work that has already landed. As a defense, also rebase the worktree onto the latest target branch before the agent starts, so any post-branch-cut commits are visible.

## Pre-commit hook policy

`.pre-commit-config.yaml` mirrors the GitHub Actions CI workflow exactly: every check that fails in CI will fail on commit, locally, with the same arguments. This is intentional — it shortens the feedback loop from "wait for CI" to "wait for `git commit`".

**One deliberate, mirrored optimization:** the `pytest` step is gated on whether any Python or JSON (including JSON Schema) files changed. A docs-only commit skips the suite in *both* places — the pre-commit hook uses `files: \.(py|json)$`, and CI's `test` job runs a "Detect Python/JSON changes" step and guards the pytest step with `if: steps.changes.outputs.code == 'true'`. CI's job still runs (so the required "Tests" status check keeps reporting); only the pytest step is skipped. Because the same `.py`/`.json` trigger governs both, the mirror is preserved: for any given set of staged changes, local and CI make the identical run/skip decision. If you change one side's gate, change the other in the same commit.

**Never bypass the pre-commit hook.** Do not run `git commit --no-verify`, do not set `SKIP=...`, do not edit `.pre-commit-config.yaml` to silence checks rather than fix them, and do not delete `.git/hooks/pre-commit`. If the hook is failing, fix the underlying issue — the failure is the system working as designed.

The only legitimate reason to change the hook config is to keep it in sync with `.github/workflows/ci.yml` when CI changes; the two must stay aligned.

## Versioning policy

Every PR that changes runtime, schema, or user-visible plugin behavior must bump the version in **all three** files in lockstep:

- `.claude-plugin/plugin.json` — `version` field
- `pyproject.toml` — `version` field
- `.claude-plugin/marketplace.json` — `plugins[0].version` field

The three versions must be **equal** at all times. CI's `version-bump` job fails the PR if any of the three is unchanged vs. base, or if the values disagree.

**When to bump which component (semver):**

- **Patch (`0.2.0` → `0.2.1`)** — bug fixes, doc-only changes, internal refactors, CI/test/chore changes, new negative tests. Anything that doesn't change what a world author or plugin user observes.
- **Minor (`0.2.0` → `0.3.0`)** — new commands, new MCP tools, new optional schema fields, new validator warnings, new skill content. Additive, backwards-compatible.
- **Major (`0.2.0` → `1.0.0`)** — schema breaking changes (renamed/removed fields, stricter required-ness), removed commands or tools, renamed MCP tool surfaces, anything that would force a world author to edit existing `world.json` files. **Pre-1.0 exception:** while the project is still pre-1.0, renamed MCP tool surfaces are treated as **minor** bumps rather than major — pre-1.0 semver conventionally allows breaking changes in minor increments.

**Platform world-schema version bumps** (e.g. v2.2 → v2.4) don't get their own tier — classify by what the change does to *existing worlds*, not by the size of the version jump:

- **Minor** if the validator accepts both the old and new shapes and no existing `world.json` is forced to change. A shape change the plugin reads bidirectionally is additive from a user's perspective; renaming the plugin's own schema artifacts (`world_vX.Y.schema.json`, `WORLD_JSON_SCHEMA_vX.Y.md`) is an internal file move, not a schema field rename, and doesn't trip major on its own. This is what v2.2 → v2.4 was (`0.17.0`).
- **Major** if a previously-valid world becomes unreadable or newly invalid — a shape the validator can no longer parse, a field that becomes required, or a removal with no back-compat path.

Whenever a bump renames a schema artifact, grep the whole repo for the old filenames **and** for prose currency claims (`v2.2 schema`, `as of v2.2`, `the v2.2 enum`) — the link tests catch paths, not sentences. Keep "New in v2.2" / "deprecated as of v2.2" provenance notes; only update claims that assert which version is *current*.

**Workflow:**

1. When starting a branch, decide the bump level based on the planned change. If you don't know yet, default to patch and revisit before opening the PR.
2. Bump `plugin.json`, `pyproject.toml`, and `marketplace.json` in the same commit as the change that warrants the bump — not in a separate "version bump" commit at the end. That way `git blame` on the version line points at the change, not at bookkeeping. (`pyproject.toml` also pins the project version in `uv.lock`; run `uv lock` so the lock matches, or CI's `uv sync --locked` will fail on drift.)
3. Fill in the "Version bump" section of the PR template with the from→to and the reason (which semver tier and why).

**Don't:**

- Don't open a PR without bumping. CI will fail it, and rerunning CI after pushing the bump wastes a cycle.
- Don't bump only some of the files. All three (`plugin.json`, `pyproject.toml`, `marketplace.json`) must move together, and `uv.lock` must be refreshed. CI will fail it otherwise.
- Don't bump in a trailing "chore: bump version" commit. Bundle it with the substantive change.
- Don't skip the bump for "trivial" doc tweaks. The bump is what guarantees every merge to `main` is a distinct, addressable version — useful for bisecting and for `/plugin` users who want to know whether they've already pulled a given change.

## Running the MCP server

```bash
uv run python -m iw_architect.server
```

(`.venv/bin/python -m iw_architect.server` also works once the venv is built.)

## Source-of-truth rules (from DESIGN_BRIEF_v2.md §3)

1. **`example-world-schema-v2.4.json` is the schema.** If `validate_world` reports errors on the fixture, the validator is wrong — fix the validator to accept the fixture. (`example-world-schema-v2.2.json` and `example-world-schema-v2.1.json` are retained as back-compat fixtures — they must still validate with only warnings, never errors. v2.2 is load-bearing: it is the only fixture carrying the pre-v2.4 bare-array shape for `triggerPrereqs` / `triggerBlockers`.)
2. **Read before writing.** Always call `Read` on the JSON before any `Edit`.
3. **Pass-through preservation.** Unknown fields survive because the agent edits in place.
4. **`schemaVersion` is load-bearing.** Read and write it on every world.
5. **The validator enforces; the schema doc explains; the fixture is ground truth.**
6. **The wiki can be stale.** [`infiniteworlds.mywikis.wiki`](https://infiniteworlds.mywikis.wiki/) documents some pre-v2.1 conventions that have since been consolidated or renamed (e.g., the wiki shows `canContinueEndedGame` as a standalone boolean; v2.1 actually folds that semantic into `effectEndsGame.data`). When the wiki and `world_v2.4.schema.json` / `example-world-schema-v2.4.json` disagree, the schema and fixture win — and flag the divergence so the docs can be updated.

## Design constraints

- **No write tools.** The plugin has no add/modify/remove MCP tools. The agent edits `world.json` directly with Claude Code's native `Read`, `Edit`, `Write` tools.
- **Single source of schema truth.** `references/world_v2.4.schema.json` is the canonical schema artifact. `validator.py` enforces it (Tier 1 jsonschema + Tier 2 custom checks). `schema_model.py` derives `SCHEMA_SUMMARY` from it at import time for the LLM-facing summary. When the platform schema evolves, edit the JSON Schema — the rest follows.
- **Warn, don't error** on unknown top-level keys, unknown effect types, and future schema versions — the platform may add fields the validator doesn't know about. Build-time strictness is enforced separately by `test_fixture_schema_coverage_nested` in `tests/test_round_trip.py`.

## Adding a new platform feature

The JSON Schema is the single edit point — `SCHEMA_SUMMARY` derives from it automatically, so there is no second place to update.

1. **Edit the JSON Schema** at `references/world_v2.4.schema.json`:
   - For a new top-level field: add an entry to `properties` with `description`, `x-iw-category`, optionally `default`, `x-iw-note`, `enum`.
   - For a new entity field: add it under the relevant `$defs.<entity>.properties`. If required, also add the field name to that `$defs.<entity>.required` array.
   - For a new effect/condition type: add an entry to `$defs.triggerEffect.x-iw-effect-types` or `$defs.triggerCondition.x-iw-condition-types`. Register the type in `validator.py`'s `_KNOWN_EFFECT_TYPES` / `_KNOWN_CONDITION_TYPES` set so it stops warning as "unknown".
2. **Add cross-reference checks** to `validator.py` if the new field references other entity IDs (e.g. tracked-item, instruction-block, trigger IDs).
3. **Add a negative test** in `tests/test_validator.py` that constructs a world violating the new rule and asserts `validate_world` reports it.
4. **Run `uv run pytest`.** The fixture round-trip (§6.1) and nested coverage tests (§6.2) will catch any drift between the schema and the canonical fixture.

`schema_model.SCHEMA_SUMMARY` and `get_schema_summary()` update automatically — no manual edit needed.

## Reference file naming convention

Markdown reference files in `references/` and its subdirectories (`fields/`, `mechanics/`, `guidance/`, `patterns/`, `templates/`) use **UPPER_SNAKE_CASE** (e.g., `FIELD_ALLOCATION_STRATEGY.md`, `TRIGGER_EVENTS.md`). This matches the repo's existing `.md` convention (CLAUDE.md, DESIGN_BRIEF_v2.md, etc.). Do not rename files to kebab-case.

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

## Agents

### Authoring agent

- **`world-architect`** (plugin, `agents/world-architect.md`, color: magenta) — Autonomous expert for designing, building, editing, and debugging Infinite Worlds story worlds. Owns the full edit-flow contract: reads world JSON, follows the reference hierarchy (schema → fixture → references → wiki), mints proper IDs, shows diffs for approval, edits in place, validates, and audits. Invoked when the user wants to author or debug world content.

### Review agents

Two read-only reviewers live alongside this repo — invoke whichever applies, sometimes both:

- `iw-architect-reviewer` (project, `.claude/agents/`, opus) — IW domain correctness: does the change model real IW workflows? Are reference docs accurate to IW mechanics? Schema/fixture/doc/validator in sync? Also handles `world.json` review and IW platform-knowledge questions.
- `plugin-dev-reviewer` (global, `~/.claude/agents/`, opus) — Claude Code plugin best practices: frontmatter, triggering examples, progressive disclosure, manifest correctness.

A change that touches both dimensions (e.g., a new command — Claude Code structure AND IW workflow assumptions) warrants both. A pure structural edit (hook, agent file, manifest housekeeping) needs only `plugin-dev-reviewer`. A `world.json` edit or IW platform question needs only `iw-architect-reviewer`. Both produce severity-tagged findings; neither modifies files.

**Agent relationship:**
- **`world-architect`** *makes the change* — authors/edits worlds, answers platform questions grounded in schema
- **Review agents** *check the change* — one examines IW domain correctness, the other examines Claude Code plugin structure
