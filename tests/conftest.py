"""conftest.py — shared pytest configuration and path setup.

Adds the hooks/ directory to sys.path so that ``citation_gate`` (a standalone
stdlib-only module, not part of the iw_architect package) is importable in
tests without installing it as a package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HOOKS_DIR = str(Path(__file__).parent.parent / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)
