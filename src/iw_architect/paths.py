"""Absolute-path guard shared by every path-taking MCP tool.

Each MCP tool runs inside the ``iw-json-tools`` server process, whose working
directory is **not** the agent's session directory. A relative path therefore
cannot be resolved to the file the author means — ``Path.resolve()`` would join
it to the server's cwd, not the session's, producing a bogus absolute path and a
confusing "file not found" error. So all path-taking tools require an absolute
path; a leading ``~`` is expanded to the home directory first.

This module centralizes the rejection *message* (so it reads identically across
tools) while leaving each tool free to wrap it in its own return envelope.
"""

from __future__ import annotations

import os
from pathlib import Path


def relative_path_message(path: str) -> str:
    """Actionable error text for a rejected relative path.

    Names the server's working directory so the process-boundary cause is
    visible to the calling agent, and tells it how to recover.
    """
    return (
        f"'{path}' is a relative path. This MCP tool requires an absolute path: "
        f"it runs in a separate process whose working directory ({os.getcwd()}) is "
        f"not your session's, so a relative path cannot be resolved to the file you "
        f"mean. Join it with your session's current working directory to form an "
        f"absolute path, then call again."
    )


class RelativePathError(FileNotFoundError):
    """Raised when a path-taking tool receives a relative path.

    Subclasses ``FileNotFoundError`` deliberately: every tool already converts
    ``FileNotFoundError`` into its own JSON/text error envelope, so this single
    exception type surfaces (with its actionable message) through all of those
    contracts unchanged, while the type name stays honest at the raise site.
    """


class WorldReadError(FileNotFoundError):
    """Raised when a world path exists but cannot be read as UTF-8 text.

    Covers a directory, an unreadable file, and non-UTF-8 bytes. Subclasses
    ``FileNotFoundError`` for the same reason as ``RelativePathError``: every
    tool's existing ``FileNotFoundError`` handler reports it in that tool's own
    error envelope instead of letting it propagate.
    """


def read_world_text(path: Path, world_path: str) -> str:
    """Read a world file as UTF-8, or raise ``WorldReadError``.

    ``world_path`` is the caller's original argument, used in the message.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise WorldReadError(f"Could not read world file {world_path}: {exc}") from exc


def require_absolute(path: str) -> Path:
    """Expand ``~`` and return an absolute ``Path``, or raise ``RelativePathError``.

    The returned path is intentionally *not* resolved against the filesystem
    (no symlink or ``..`` collapsing); callers do that themselves where needed.
    """
    expanded = Path(os.path.expanduser(path))
    if not expanded.is_absolute():
        raise RelativePathError(relative_path_message(path))
    return expanded
