"""Play Probe C: does `firedThisTurn` narrow a prereq/blocker gate to the current turn?

    python play_probe_c.py <outdir> [--resume]

The one-shot anchor fires on turn 1 and never again, so from turn 2 it has fired at some
point but not this turn. Three turns of World Debug output split the four P2 cells (see
`build_probe_c.py` for the prediction table). The same transcripts also carry the runtime
half of P14: P14b/P14c are conditionless after import (predicted dead), while P14d/P14e/P14f
survived import and should show up as either firing or erroring in the Triggers panel.

Reuses play_probe_d's machinery with the title swapped.
"""

from __future__ import annotations

import sys
from pathlib import Path

import iwdrive as d
import play_probe_d as pd
from playwright.sync_api import sync_playwright

pd.TITLE = "SCHEMA PROBE C - PawScript malformed input, firedThisTurn"
TURNS = (2, 3)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(exist_ok=True)
    resume = "--resume" in sys.argv[2:]
    with sync_playwright() as pw:
        pg = d.our_page(pw.chromium.connect_over_cdp(d.CDP).contexts[0])
        if resume:
            d.settle_dialogs(pg, 1500)
        else:
            pd.start_new_game(pg, out)
        pd.set_option(pg, "Illustration options", "never")
        pd.enable_world_debug(pg)
        (out / "turn1-debug.txt").write_text(pd.debug_modal(pg))
        (out / "turn1-items.txt").write_text(pd.tracked_items(pg))
        for turn in TURNS:
            pd.take_turn(pg, turn, out)
        print("done")


if __name__ == "__main__":
    main()
