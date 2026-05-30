# Usage Examples — Directory Layouts & Command Patterns

This guide shows **how people actually organize their work** when authoring Infinite Worlds
worlds with this plugin. None of these layouts are enforced by the tooling — the plugin only
ever needs a single `world.json` to point its commands and MCP tools at. Everything else here
is convention that has proven useful for keeping long-lived worlds maintainable.

Use it as a menu, not a mandate: skim the three patterns below, pick the one that matches how
much history and review rigor your world needs, and adapt freely.

> **The one hard rule:** the platform consumes a single `world.json`. Whatever you name your
> working files, the artifact you upload/export is one JSON document that passes
> `validate_world`. The patterns below are all about *how you get to that file safely*.

---

## Prerequisites: the three things the plugin gives you

Before the layouts, a quick refresher on what you're invoking (see the
[README](./README.md#using-the-plugin) for the full table):

- **Slash commands** — structured, multi-turn workflows:
  - `/infinite-worlds-architect:new-world <output_path>` — guided creation from scratch
  - `/infinite-worlds-architect:modify-world <world_path>` — guided field-by-field editing
  - `/infinite-worlds-architect:spinoff-world <source_path> <target_path>` — derive a variant
- **The `world-architect` agent** — reached automatically when you describe authoring/debugging
  work in natural language ("add a wandering merchant NPC", "my trigger won't fire").
- **MCP tools** — `validate_world`, `audit_world`, `format_world_for_review`, `compare_worlds`,
  `get_diff_summary`, `scaffold_world`, `mint_ids`, etc. You rarely call these directly; the
  agent and commands do. But knowing they exist helps you ask for specific operations.

The minimal viable layout is just:

```text
my-world/
└── world.json        # the only file the platform actually needs
```

Everything below is what you add as a world grows past "one sitting."

---

## Pattern A — Draft → Review → Finalize

**Best for:** narrative-heavy worlds where you want a human-readable proof of each version before
committing to it, and where you iterate on prose (descriptions, instructions, triggers) a lot.

```text
my-world/
├── world_v1.8.json                 # current working version
├── world_v1.8.review.md            # format_world_for_review output for v1.8
├── world_v1.9_draft.json           # next version, in progress
├── feature-x_proposal.md           # design doc written BEFORE implementing a big change
└── older_versions/
    ├── world_v1.7.json
    ├── world_v1.6.json
    └── turn_33_export.txt           # raw platform exports kept for reference
```

**The loop:**

1. Write a `*_proposal.md` first for any substantial feature (a new NPC, a plot twist, a
   mechanics change). This is a design discussion you and Claude lock down *before* touching
   JSON, so the edit pass is mechanical rather than exploratory. You can write the proposal or Claude can write the proposal for you.
2. Review the proposal and make any changes you want to it.
3. When ready, instruct Claude (using the world-architect agent) to implement the changes. Claude will then implement the changes in a copy of your world.json, leaving the original unchanged (hopefully - be explicit in your instructions if you're unsure).
4. If you want to review the changes for the draft world more easily, you can ask Claude to make your draft world into a markdown document for easier reviewing.
   ```text
   Claude, run format_world_for_review on ./my-world/world_v1.9_draft.json
   ```
   This writes `world_v1.9_draft.review.md` next to the JSON. Read *that*, not the JSON.
5. When the draft is good, import the draft JSON into Infinite Worlds, and move the prior version
   into `older_versions/`.

**Why the paired `.review.md` matters:** the JSON is dense and easy to misread; the review
render flattens it into the sections a reader actually experiences (Description, Background,
Main Instructions, characters, triggers). It's your diff-against-intent safety net.

---

## Pattern B — Semantic Version History

**Best for:** worlds you'll maintain over many sessions, where you want a clean numbered trail
and a written record of *what each bump taught you*.

```text
my-world/
├── my_world_v1.16.json
├── my_world_v1.17.json
├── my_world_v1.17.1.json           # patch-level fix on top of v1.17
├── docs_v1.14_lessons.md           # "what changed and why" for a version range
├── feature_plan.md                 # forward-looking plan for an upcoming feature
├── scaffold_world_manual_add.json  # scratch artifacts from a scaffold/merge step
└── old_files/
    ├── my_world_v1.04.json
    ├── my_world_v1.05.json
    └── ...                          # every superseded version, archived not deleted
```

**Conventions that make this work:**

- **Monotonic semver-ish filenames** (`v1.16` → `v1.17` → `v1.17.1`). Minor bumps for additive
  changes, patch suffixes for fixes. The newest number is always the live file.
- **`docs_vX_lessons.md`** — after a meaningful jump, write down what changed field-by-field and
  *why*. Future-you (and future Claude) reads this instead of diffing two 30 KB JSON files by
  hand. A good lessons doc has `**What changed:**` / `**Why:**` pairs per change.
- **`old_files/`** — archive, don't delete. Superseded versions are cheap to keep and priceless
  when you need to recover a sentence or trace a regression.

**Diffing two versions** without reading either file end-to-end:

```text
Claude, run get_diff_summary on
  ./my-world/old_files/my_world_v1.16.json and ./my-world/my_world_v1.17.json
```

`get_diff_summary` gives a narrative ("added character X, changed trigger Y's condition");
`compare_worlds` gives the structural diff. Both keep the raw JSON out of the conversation.

---

## Cross-cutting conventions

These show up across all three patterns; mix and match.

| Convention | What & why |
|---|---|
| **Review renders** | `format_world_for_review` → `<stem>.review.md`. Easier sometimes to read the render, not the raw JSON. |
| **Archive, don't delete** | `old_files/` or `older_versions/` for superseded versions — cheap insurance against regressions. |
| **Proposals before big edits** | A `*_proposal.md` / `*_plan.md` locks design *before* JSON changes, so editing is mechanical. |
| **Lessons docs** | `docs_vX_lessons.md` records *what changed and why* so nobody re-diffs huge files by hand. |
| **Validate after every change** | `validate_world` is the gate: if it fails, the platform would reject the world. |

---

## A note on Git (recommended)

Each of the example worlds above is its own Git repository. You don't strictly need version
control — the `old_files/` archive pattern works on its own — but a repo per world gives you:

- A real diff/blame history instead of filename-encoded versions.
- The ability to branch experimental directions (a risky plot twist, an NSFW spinoff) without
  disturbing the known-good `world.json`.
- A safe place to keep the throwaway helper scripts and proposal docs without cluttering the
  world itself.

If you work in a repo, prefer branching for any non-trivial change and keeping `main` as the
last-known-good world. (This mirrors the discipline the plugin repo itself follows — see its
`CLAUDE.md`.)

---

## Quick reference: which pattern do I want?

| If you… | Use |
|---|---|
| Iterate heavily on prose and want to *read* each version before trusting it | **Pattern A** (Draft → Review → Finalize) |
| Maintain a world over many sessions and want a clean numbered trail | **Pattern B** (Semantic Version History) |
| Are just starting | One `world.json` + `validate_world`. Add structure only when you need it. |
