"""Play Probe D: start a new game on the imported world, set Lynx / no illustrations, turn on
World Debug, then take `wait` turns and capture body / debug panel / tracked items per turn.

    python play_probe_d.py <outdir> [--resume]

`--resume` skips the Play → Choose-character → model steps when a previous run died mid-way
and the game is already on the play screen. Every turn spends credits (Lynx: ~21-26 each).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import iwdrive as d
from playwright.sync_api import Page, sync_playwright

TITLE = "Probe D - PawScript runtime"
TURNS = (2, 3, 4)  # turn 1 is the opening IW generates at game start
TURN_TIMEOUT_S = 240


def body(pg: Page) -> str:
    return pg.evaluate("() => document.body.innerText")


def credits(pg: Page) -> str:
    m = re.search(r"Credits:\s*([\d.,]+)", body(pg))
    return m[1] if m else "?"


def tracked_items(pg: Page) -> str:
    """Open the inline Tracked Items panel (toolbar database icon) and return its text."""
    t = body(pg)
    if "Tracked Items" not in t:
        pg.locator("button:has(.fa.fa-database)").locator("visible=true").first.click()
        pg.wait_for_timeout(1200)
        t = body(pg)
    seg = t.split("Tracked Items", 1)[-1]
    if "Continue waiting" in seg:
        seg = seg.split("Continue waiting")[0]
    return seg[:3000].strip()


def debug_modal(pg: Page) -> str:
    """Open World debug tools (bug icon), expand Triggers + PawScript, return the modal text."""
    pg.locator("button:has(.fa.fa-bug)").locator("visible=true").first.click()
    pg.wait_for_timeout(1500)
    for hdr in ("Triggers (", "PawScript ("):
        h = pg.locator(f'.modal :text("{hdr}")').locator("visible=true")
        if h.count():
            h.first.click()
            pg.wait_for_timeout(700)
    t = d.dialog_text(pg)
    d.close_all_modals(pg, prefer=("OK",))
    return t


def set_option(pg: Page, menu_item: str, radio_value: str) -> None:
    """Menu → <menu_item> → pick the radio with value=<radio_value> → OK."""
    d.open_menu(pg)
    pg.locator(f'button:has-text("{menu_item}")').locator("visible=true").first.click()
    pg.wait_for_timeout(1200)
    pg.locator(f".modal input[type=radio][value={radio_value}]").first.check(force=True)
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 2000)


def enable_world_debug(pg: Page) -> None:
    d.open_menu(pg)
    pg.locator('button:has-text("World debug tools")').locator("visible=true").first.click()
    pg.wait_for_timeout(1200)
    for label in ("Trigger status", "PawScript (scripts"):
        cb = pg.locator(f'.modal :text("{label}")').locator("visible=true").first
        inp = cb.locator("xpath=preceding::input[@type='checkbox'][1]")
        if not inp.is_checked():
            cb.click()
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 1500)


def start_new_game(pg: Page, out: Path) -> None:
    d.recover(pg)
    row = d.your_world_rows(pg).filter(has_text=TITLE).first
    row.get_by_role("button", name=f'Play "{TITLE}"').first.click()
    pg.wait_for_timeout(1500)
    print("confirm:", d.settle_dialogs(pg, 2000))
    d.wait_for(pg, 'button:has-text("Choose character")', 60000).click()
    opening: list[str] = []
    t0 = time.time()
    while time.time() - t0 < TURN_TIMEOUT_S:
        pg.wait_for_timeout(1000)
        t = d.dialog_text(pg)
        if t:
            opening.append(t[:120].replace("\n", " / "))
            d.close_all_modals(pg, prefer=("OK",))
        if d.vis(pg, 'button:has-text("Take action")').count() and not d.dialog_text(pg):
            break
    print("opening popups:", opening)
    print("credits after opening:", credits(pg))
    (out / "turn1-body.txt").write_text(body(pg))
    set_option(pg, "AI model", "lynx")


def take_turn(pg: Page, turn: int, out: Path) -> None:
    pg.locator("textarea").locator("visible=true").first.fill("wait")
    c0 = credits(pg)
    t0 = time.time()
    d.vis(pg, 'button:has-text("Take action")').first.click()
    while time.time() - t0 < TURN_TIMEOUT_S:
        pg.wait_for_timeout(1000)
        if d.dialog_text(pg):
            d.close_all_modals(pg, prefer=("OK",))
        if f"turn {turn}" in body(pg) and d.vis(pg, 'button:has-text("Take action")').count():
            break
    print(f"turn {turn}: {time.time() - t0:.0f}s, credits {c0} -> {credits(pg)}")
    (out / f"turn{turn}-body.txt").write_text(body(pg))
    (out / f"turn{turn}-debug.txt").write_text(debug_modal(pg))
    (out / f"turn{turn}-items.txt").write_text(tracked_items(pg))


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(exist_ok=True)
    resume = "--resume" in sys.argv[2:]
    with sync_playwright() as pw:
        pg = d.our_page(pw.chromium.connect_over_cdp(d.CDP).contexts[0])
        if resume:
            d.settle_dialogs(pg, 1500)
        else:
            start_new_game(pg, out)
        set_option(pg, "Illustration options", "never")
        enable_world_debug(pg)
        (out / "turn1-debug.txt").write_text(debug_modal(pg))
        (out / "turn1-items.txt").write_text(tracked_items(pg))
        print("turn1 items:\n" + tracked_items(pg)[:1500])
        for turn in TURNS:
            take_turn(pg, turn, out)
        print("done")


if __name__ == "__main__":
    main()
