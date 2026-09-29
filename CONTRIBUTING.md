# Contributing

Setup, the pre-commit policy, the versioning policy and the "adding a platform feature"
workflow live in [`CLAUDE.md`](CLAUDE.md). This file covers the conventions that aren't
recorded there.

## Branches

Never commit directly to `main` — it is branch-protected and always shippable. Work on a
branch and open a PR.

Name the branch `<type>/<short-kebab-description>`, where `<type>` matches the PR
template's "Type of change":

| Prefix | Use for |
|---|---|
| `feat/` | New capability — commands, MCP tools, validator warnings, reference content |
| `fix/` | Bug fixes, including incorrect claims in reference docs |
| `refactor/` | Internal restructuring with no behavior change |
| `docs/` | Documentation-only changes |
| `test/` | Test-only changes |
| `ci/` | GitHub Actions and pre-commit config |
| `chore/` | Housekeeping — dependency bumps, tooling |

Examples: `feat/search-turns-tool`, `fix/character-index-skip-tracked-sections`.

Worktrees created with Claude Code's `EnterWorktree` start on a `worktree-<name>` branch.
Rename it before pushing: `git branch -m feat/<description>`.

## Commits and PR titles

Use a [Conventional Commits](https://www.conventionalcommits.org/) type prefix, with the
same type as the branch. PRs are squash-merged, so the PR title becomes the commit on
`main`. Put the version the PR ships in the title:

```
feat: search_turns MCP tool — keyword/regex search over story turns (v0.24.0)
```

Every PR that changes plugin behavior bumps the version, and PRs that ship docs only
bump it too. See "Versioning policy" in `CLAUDE.md`. If another PR claiming the same
version merges first, rebase and bump again.
