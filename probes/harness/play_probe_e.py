"""Play Probe E: start a new game on the imported world and take two `wait` turns.

    python play_probe_e.py <outdir> [--resume]

The only runtime question is Q10: does the absent-`triggerConditions`-key trigger
(normalized to `[]` at import) ever fire, while the always-true control gate fires
every turn? Two turns of World Debug output settle it. Reuses play_probe_d's
machinery with the title swapped.
"""

from __future__ import annotations

import sys
from pathlib import Path

import iwdrive as d
import play_probe_d as pd
from playwright.sync_api import sync_playwright

pd.TITLE = "SCHEMA PROBE E - scope level, model control, absent conditions key"
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
        print("turn1 items:\n" + pd.tracked_items(pg)[:1500])
        for turn in TURNS:
            pd.take_turn(pg, turn, out)
        print("done")


if __name__ == "__main__":
    main()
