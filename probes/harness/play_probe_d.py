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
    """Credit balance from the top bar.

    Reads the 'Credits: N' text (pre-2026-09) or the credits button, whose aria-label is
    'N credits' or 'N credits, X of Y free turns left today'."""
    b = pg.locator('button[aria-label*=" credits"]').locator("visible=true")
    if b.count():
        m = re.match(r"\s*([\d.,]+)\s+credits", b.first.get_attribute("aria-label") or "")
        if m:
            return m[1]
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


MENU_PATHS = {
    # 2026-09 UI: "AI model" is a top-level menuitem; the rest moved under "Settings".
    "AI model": ("AI model",),
    "Illustration options": ("Settings", "Illustration options"),
    "World debug tools": ("Settings", "World debug tools"),
}


def open_option(pg: Page, menu_item: str) -> None:
    """Open the dialog for a menu option under either menu layout."""
    try:
        d.menu_path(pg, *MENU_PATHS.get(menu_item, (menu_item,)))
    except d.MenuEntryMissing:
        d.menu_click(pg, menu_item)  # pre-2026-09 flat button menu
    pg.wait_for_timeout(1200)


def set_option(pg: Page, menu_item: str, radio_value: str, select_label: str | None = None) -> None:
    """Menu → <menu_item> → pick radio value=<radio_value> (or, when the dialog uses a
    <select>, the option whose label is <select_label>) → OK."""
    open_option(pg, menu_item)
    radio = pg.locator(f".modal input[type=radio][value={radio_value}]")
    if radio.count():
        radio.first.check(force=True)
    elif select_label and pg.locator(".modal select").locator("visible=true").count():
        pg.locator(".modal select").locator("visible=true").first.select_option(label=select_label)
    elif select_label:  # radios labelled ": Lynx" etc. without a usable value attribute
        pg.locator(f'.modal :text("{select_label}")').locator("visible=true").first.click()
    else:
        raise SystemExit(f"{menu_item}: no radio {radio_value!r} and no select label given")
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 2000)


WORLD_DEBUG_DEFAULT = ("Trigger status", "PawScript (scripts")


def enable_world_debug(
    pg: Page, labels=WORLD_DEBUG_DEFAULT, log_options: Path | None = None
) -> None:
    """Tick the given World debug tools checkboxes (by label text). `labels="all"` ticks
    every checkbox in the dialog; `log_options` saves the dialog text (the option list)."""
    open_option(pg, "World debug tools")
    if log_options:
        log_options.write_text(d.dialog_text(pg))
    boxes = pg.locator(".modal input[type=checkbox]").locator("visible=true")
    if labels == "all":
        for i in range(boxes.count()):
            if not boxes.nth(i).is_checked():
                boxes.nth(i).check(force=True)
    else:
        for label in labels:
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
