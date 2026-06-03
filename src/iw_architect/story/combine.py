"""combine.py — read + merge one or more story-export text files.

Multi-file rules (from spec §2):
- Sort files by mtime ascending before merging.
- Same turn number in 2 files → keep the entry from the latest-mtime file.
- Header comes from the newest file.
- Turn-number gaps → warning, never an error.
- No Turn 1 in the merged set → ValueError.

Returned dict shape::

    {
        "header": str,          # text before the first turn marker
        "turns": [              # deduplicated, sorted ascending by number
            {
                "number": int,
                "content": str,     # raw text of the turn body (after marker line)
                "source": str,      # absolute path of the file this turn came from
                "mtime": float,     # os.path.getmtime of that source file
            }
        ],
        "combined_text": str,   # header + all kept-turn bodies concatenated (LF-normalised)
        "warnings": [str],
    }
"""

import os
import re

_TURN_MARKER = re.compile(r"^-- Turn (\d+) --\r?$", re.MULTILINE)


def _normalise(text: str) -> str:
    """Normalise CRLF → LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_turns(text: str, source: str, mtime: float) -> tuple[str, list[dict]]:
    """Return (header_text, [turn_dicts]) for one file's normalised text."""
    norm = _normalise(text)
    matches = list(_TURN_MARKER.finditer(norm))
    if not matches:
        header = norm
        return header, []

    header = norm[: matches[0].start()]
    turns = []
    for i, m in enumerate(matches):
        number = int(m.group(1))
        body_start = m.end() + 1  # skip the newline after the marker
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(norm)
        content = norm[body_start:body_end]
        turns.append(
            {
                "number": number,
                "content": content,
                "source": os.path.abspath(source),
                "mtime": mtime,
            }
        )
    return header, turns


def combine(file_paths: list[str]) -> dict:
    """Merge one or more story-export files into a single turn sequence.

    Parameters
    ----------
    file_paths:
        Absolute or relative paths to ``.txt`` export files.

    Returns
    -------
    dict with keys ``header``, ``turns``, ``combined_text``, ``warnings``.

    Raises
    ------
    ValueError
        If no Turn 1 is present after merging all files.
    """
    if not file_paths:
        raise ValueError("No files provided")

    # Sort ascending by mtime (oldest first) so newer entries overwrite older ones.
    sorted_paths = sorted(file_paths, key=lambda p: os.path.getmtime(p))

    all_turns: dict[int, dict] = {}  # number → turn dict (newest mtime wins)
    header_text = ""

    for path in sorted_paths:
        mtime = os.path.getmtime(path)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        header, turns = _split_turns(raw, path, mtime)
        # Header from newest file (last in sorted order), but never let a
        # header-less re-export clobber a real header from an older file.
        if header.strip():
            header_text = header
        for t in turns:
            existing = all_turns.get(t["number"])
            if existing is None or t["mtime"] >= existing["mtime"]:
                all_turns[t["number"]] = t

    # Sort turns ascending by number.
    sorted_turns = sorted(all_turns.values(), key=lambda t: t["number"])

    if not any(t["number"] == 1 for t in sorted_turns):
        raise ValueError("No Turn 1 found; extraction failed")

    # Detect gaps.
    warnings: list[str] = []
    numbers = [t["number"] for t in sorted_turns]
    for i in range(len(numbers) - 1):
        if numbers[i + 1] != numbers[i] + 1:
            warnings.append(
                f"Turn gap detected: turns {numbers[i]} and {numbers[i + 1]} are not consecutive"
            )

    combined_text = header_text + "".join(
        f"-- Turn {t['number']} --\n{t['content']}" for t in sorted_turns
    )

    return {
        "header": header_text,
        "turns": sorted_turns,
        "combined_text": combined_text,
        "warnings": warnings,
    }
