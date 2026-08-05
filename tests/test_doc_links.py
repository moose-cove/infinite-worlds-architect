"""Documentation link-integrity tests.

The reference tree under ``references/`` is the plugin's on-demand authoring library: the
``world-architect`` agent follows those links mid-task, so a dead link is a dead end for the
agent, not a cosmetic docs nit. Two real defect classes have shipped to ``main`` already —
wrong-depth ``../../`` links, and schema filenames left stale by a rename that landed in a
different PR than the file referencing them. Neither is visible in the diff of the PR that
breaks it, so review cannot catch them. These tests can.

Three tiers, cheapest and most certain first:

1. :func:`test_relative_links_resolve` — every ``[text](path)`` target exists.
2. :func:`test_link_anchors_resolve` — every ``[text](path#anchor)`` anchor matches a heading.
3. :func:`test_inline_code_paths_resolve` — every path-shaped ``\\`inline code\\`` span resolves.

Tier 3 is the heuristic one, and the only one that would have caught the stale-schema-filename
bug: that reference was inline code, not a Markdown link, so no ordinary link checker sees it.
Its skip rules are deliberately conservative — see :data:`_PLACEHOLDER_PREFIXES` and
:data:`_EXCLUDED_FROM_INLINE_PATHS`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

# Directories whose Markdown is part of the shipped, live documentation surface.
_DOC_GLOBS = ("references/**/*.md", "commands/*.md", "agents/**/*.md", "*.md")

# `dev-docs/` is a frozen historical record (DESIGN_BRIEF_v2.md describes the original v2.1
# build and names v2.1 artifacts on purpose). Rewriting it to match today's tree would destroy
# the history it exists to preserve, so it is out of scope for every tier.
_EXCLUDED_DIRS = ("dev-docs",)

# Extensions worth resolving. Anything else in a link (images, external assets) is ignored.
_PATH_SUFFIXES = (".md", ".json", ".py", ".yaml", ".yml", ".toml")

# Inline-code spans starting with these are placeholders or templated paths, not repo
# references: URLs, absolute example paths (`/path/sequel.json`), shell/template variables
# (`${CLAUDE_PLUGIN_ROOT}/...`), and `@`-prefixed plugin-load syntax.
_PLACEHOLDER_PREFIXES = ("http", "/", "$", "<", "@", "~")

# CHANGELOG.md names artifacts as they existed at each released version — its references to
# `references/world_v2.1.schema.json` are correct history and must stay stale.
_EXCLUDED_FROM_INLINE_PATHS = ("CHANGELOG.md",)

# `[text](target)` — target captured up to a `#` anchor or the closing paren.
_LINK_RE = re.compile(r"\]\(([^)\s#]+)(#[^)\s]*)?\)")
# A path-shaped inline-code span: `some/path.md`.
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_HEADING_RE = re.compile(r"\s{0,3}#{1,6}\s+(.*)")
# GitHub disambiguates duplicate headings with a numeric suffix (`#name`, `#name-1`).
_DUP_ANCHOR_RE = re.compile(r"^(.*)-(\d+)$")


def _doc_files() -> list[Path]:
    """Every live documentation Markdown file, symlinks excluded.

    The tracked root ``WORLD_JSON_SCHEMA_v2.4.md`` symlink points into ``references/``, so its
    relative links resolve against ``references/`` — not the repo root where the symlink sits.
    Checking it as if it were a root-level file reports phantom breakage for links that are
    actually fine, so symlinks are skipped and the real file is checked in place.
    """
    seen: set[Path] = set()
    for pattern in _DOC_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_symlink() or not path.is_file():
                continue
            if any(part in _EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
                continue
            seen.add(path)
    return sorted(seen)


def _strip_fenced_blocks(text: str) -> str:
    """Drop ```-fenced blocks.

    Fenced blocks hold example JSON, directory trees, and PawScript snippets whose `#` comment
    lines would otherwise be read as Markdown headings, and whose paths are illustrative rather
    than real references.
    """
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def _github_anchor(heading: str) -> str:
    """Slugify a heading the way GitHub does.

    Lowercase, drop everything that is not a word character/space/hyphen, then map each space to
    one hyphen. Whitespace is deliberately **not** collapsed: ``## 8 Image prompt details (world
    + per-character)`` drops the ``+`` but keeps both surrounding spaces, yielding the
    double-hyphen ``...world--per-character``. Collapsing here would report working anchors as
    broken.
    """
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return slug.replace(" ", "-")


def _anchors_of(path: Path) -> set[str]:
    """Every anchor GitHub would generate for the headings in ``path``."""
    return {
        _github_anchor(m.group(1))
        for line in _strip_fenced_blocks(path.read_text()).splitlines()
        if (m := _HEADING_RE.match(line))
    }


def _is_checkable(target: str) -> bool:
    if target.startswith(_PLACEHOLDER_PREFIXES) or "${" in target:
        return False
    return target.endswith(_PATH_SUFFIXES)


def _format(failures: list[str], tier: str) -> str:
    listing = "\n".join(f"  {f}" for f in failures)
    return f"{len(failures)} unresolved {tier}:\n{listing}"


@pytest.mark.parametrize("doc", _doc_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_relative_links_resolve(doc: Path):
    """Tier 1: every relative Markdown link target exists on disk."""
    failures = [
        f"{doc.relative_to(REPO_ROOT)} -> {target}"
        for target, _ in _LINK_RE.findall(doc.read_text())
        if _is_checkable(target) and not (doc.parent / target).resolve().exists()
    ]
    assert not failures, _format(failures, "link target(s)")


@pytest.mark.parametrize("doc", _doc_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_link_anchors_resolve(doc: Path):
    """Tier 2: every ``#anchor`` on a Markdown link matches a heading in the target file."""
    failures = []
    for target, anchor in _LINK_RE.findall(doc.read_text()):
        if not anchor or not _is_checkable(target) or not target.endswith(".md"):
            continue
        resolved = (doc.parent / target).resolve()
        if not resolved.exists():
            continue  # tier 1 owns missing files; don't double-report
        wanted = anchor.lstrip("#")
        anchors = _anchors_of(resolved)
        if wanted in anchors:
            continue
        # `#name-1` is GitHub's duplicate-heading form; accept when `#name` exists.
        dup = _DUP_ANCHOR_RE.match(wanted)
        if dup and dup.group(1) in anchors:
            continue
        failures.append(f"{doc.relative_to(REPO_ROOT)} -> {target}#{wanted}")
    assert not failures, _format(failures, "link anchor(s)")


@pytest.mark.parametrize(
    "doc",
    [d for d in _doc_files() if d.name not in _EXCLUDED_FROM_INLINE_PATHS],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_inline_code_paths_resolve(doc: Path):
    """Tier 3: every path-shaped inline-code span names a file that exists.

    Resolution is tried against three roots, because the docs legitimately use all three:
    the containing file's directory, the repo root (``src/iw_architect/validator.py``), and
    ``references/`` (``references/mechanics/PAWSCRIPT.md`` writes ``fields/TRACKED_ITEMS.md``
    to mean a sibling under ``references/``).
    """
    roots = (doc.parent, REPO_ROOT, REPO_ROOT / "references")
    failures = []
    for candidate in _INLINE_CODE_RE.findall(_strip_fenced_blocks(doc.read_text())):
        target = candidate.strip()
        if "/" not in target or " " in target or "*" in target:
            continue
        if not _is_checkable(target):
            continue
        if not any((root / target).resolve().exists() for root in roots):
            failures.append(f"{doc.relative_to(REPO_ROOT)} -> {target}")
    assert not failures, _format(failures, "inline-code path(s)")
