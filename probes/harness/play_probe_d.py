"""Play Probe D: start a new game on the imported world, set Lynx / no illustrations, turn on
World Debug, then take `wait` turns and capture body / debug panel / tracked items per turn.

    python play_probe_d.py <outdir> [--resume]

`--resume` skips the Play → Choose-character → model steps when a previous run died mid-way
and the game is already on the play screen. Every turn spends credits once the day's free
turns are used (Lynx: 30-50 each as of 2026-11).
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
    """Credit balance from the top-bar credits button, whose aria-label reads
    'N credits, X of Y free turns left today' (or just 'N credits'); '?' if absent."""
    b = pg.locator('button[aria-label*=" credits"]').locator("visible=true")
    if b.count():
        m = re.match(r"\s*([\d.,]+)\s+credits", b.first.get_attribute("aria-label") or "")
        if m:
            return m[1]
    return "?"


def credits_label(pg: Page) -> str:
    """The credits button's full aria-label (balance plus free turns left), for logs."""
    b = pg.locator('button[aria-label*=" credits"]').locator("visible=true")
    return (b.first.get_attribute("aria-label") or "?") if b.count() else "?"


def tracked_items(pg: Page) -> str:
    """Open the inline Tracked Items panel and return its text.

    The toolbar database icon ("Show information on tracked items") is a toggle and the
    panel can render a beat after the click, so poll for its header, and click again only
    if it never appears."""
    t = body(pg)
    for _ in range(2):
        if "Tracked Items" in t:
            break
        pg.locator("button:has(.fa.fa-database)").locator("visible=true").first.click()
        for _ in range(10):
            pg.wait_for_timeout(500)
            t = body(pg)
            if "Tracked Items" in t:
                break
    seg = t.split("Tracked Items", 1)[-1]
    for end in ("Continue waiting", "Or type any action you want below:"):
        seg = seg.split(end)[0]
    return seg[:3000].strip()


# A collapsed World debug tools section header: a button whose leading icon is the
# right-pointing chevron (it turns to `.fa-angle-down` once expanded).
COLLAPSED_SECTION = "button:has(> i.fa-angle-right:first-child)"


def open_debug_modal(pg: Page) -> str:
    """Open World debug tools (toolbar bug icon) and expand every section; return the id of
    the modal.

    The modal is a stack of collapsible sections, all collapsed on open: "Active instructions"
    (with nested "Main instructions" and one entry per active extra instruction block),
    "Triggers" ("Triggers fired this turn" / "All triggers"), "Evaluation", "PawScript", plus
    "Inactive instructions", "Model thinking" and "Long term memory" when those debug options
    have content. Headers carry no "(N)" counts. Expanding one can reveal nested collapsed
    headers, so keep clicking the first collapsed one until none is left.
    """
    pg.locator("button:has(.fa.fa-bug)").locator("visible=true").first.click()
    pg.wait_for_timeout(1500)
    ids = d.open_modal_ids(pg)
    if not ids:
        raise RuntimeError("World debug tools modal did not open")
    modal = pg.locator(f"#{ids[-1]}")
    for _ in range(60):
        hdr = modal.locator(COLLAPSED_SECTION).locator("visible=true")
        if not hdr.count():
            break
        hdr.first.click(timeout=5000)
        pg.wait_for_timeout(500)
    else:
        print("open_debug_modal: gave up with sections still collapsed")
    return ids[-1]


def debug_modal(pg: Page) -> str:
    """Open World debug tools, expand every section, return the modal text and close it."""
    open_debug_modal(pg)
    t = d.dialog_text(pg)
    d.close_all_modals(pg, prefer=("OK",))
    return t


def sandbox_eval(pg: Page, trigger: str, expr: str) -> str:
    """Evaluate `expr` in the in-game PawScript Expression Sandbox, opened from the World
    debug tools PawScript entry for trigger `trigger`; return the sandbox's text from its
    "Result" onwards. Free: it evaluates against the turn's data without playing a turn.

    The sandbox is a second stacked modal (CodeMirror expression box, Evaluate, Share,
    Update Game, Close). Only Evaluate and Close are touched — never "Update Game"."""
    top = open_debug_modal(pg)
    # The PawScript section is flat: "Trigger:" / <name> / "PawScript condition" /
    # "Open in Sandbox" / result… with no per-entry wrapper, so walk the text nodes in
    # document order and find the link that follows this trigger's name.
    nth = pg.locator(f"#{top}").evaluate(
        """(m, want) => {
            let current = null, prevWasLabel = false, n = -1;
            const walker = document.createTreeWalker(m, NodeFilter.SHOW_TEXT);
            for (let t = walker.nextNode(); t; t = walker.nextNode()) {
                const s = t.textContent.trim();
                if (!s) continue;
                if (s === 'Open in Sandbox') { n++; if (current === want) return n; continue; }
                if (prevWasLabel) current = s;
                prevWasLabel = s === 'Trigger:';
            }
            return -1;
        }""",
        trigger,
    )
    if nth < 0:
        d.close_all_modals(pg, prefer=("OK",))
        raise RuntimeError(f"no PawScript entry with an Open in Sandbox link for {trigger!r}")
    pg.locator(f"#{top}").get_by_text("Open in Sandbox", exact=True).nth(nth).click()
    pg.wait_for_timeout(2500)
    sb = pg.locator(f"#{d.open_modal_ids(pg)[-1]}")
    box = sb.locator(".cm-editor .cm-content").locator("visible=true").last
    box.click()
    pg.keyboard.press("Control+A")
    pg.keyboard.type(expr)
    sb.get_by_role("button", name="Evaluate", exact=True).click()
    pg.wait_for_timeout(2500)
    text = sb.inner_text()
    sb.get_by_role("button", name="Close", exact=True).click()
    pg.wait_for_timeout(1000)
    d.close_all_modals(pg, prefer=("OK",))
    return text[text.find("Result") :].split("Update Game")[0].strip()


MENU_PATHS = {
    "AI model": ("AI model",),
    "Illustration options": ("Settings", "Illustration options"),
    "World debug tools": ("Settings", "World debug tools"),
}


def open_option(pg: Page, menu_item: str) -> None:
    """Open the dialog behind a menu option (see MENU_PATHS for where each one lives)."""
    d.menu_path(pg, *MENU_PATHS.get(menu_item, (menu_item,)))
    pg.wait_for_timeout(1200)


def set_option(pg: Page, menu_item: str, value: str) -> None:
    """Menu → <menu_item> → pick `value` → OK.

    "AI model" is a radio group (`value` is the radio's value, e.g. "lynx"). "Illustration
    options" holds two <select>s ("Automatically generate images", "Alternative images per
    turn"); `value` is an option label ("Never") and picks the select that offers it."""
    open_option(pg, menu_item)
    radio = pg.locator(f".modal input[type=radio][value={value}]")
    if radio.count():
        radio.first.check(force=True)
    else:
        sel = (
            pg.locator(".modal select")
            .locator("visible=true")
            .filter(has=pg.locator(f'option:text-is("{value}")'))
        )
        if sel.count() != 1:
            raise SystemExit(f"{menu_item}: no radio {value!r} and {sel.count()} selects offer it")
        sel.first.select_option(label=value)
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 2000)


WORLD_DEBUG_DEFAULT = ("Trigger status", "PawScript (scripts, conditions and the Sandbox)")


def enable_world_debug(
    pg: Page, labels=WORLD_DEBUG_DEFAULT, log_options: Path | None = None
) -> None:
    """Tick the given World debug tools checkboxes (by exact label). `labels="all"` ticks
    every visible checkbox in the dialog; `log_options` saves the dialog text (the option list).

    The menu entry only exists while Storyteller mode is on (Menu → Settings → Storyteller
    mode). This does not switch it on; it fails with a pointer to it instead."""
    try:
        open_option(pg, "World debug tools")
    except d.MenuEntryMissing as e:
        raise SystemExit(f"{e} — turn on Storyteller mode (Menu → Settings) and re-run") from e
    if log_options:
        log_options.write_text(d.dialog_text(pg))
    if labels == "all":
        boxes = pg.locator(".modal input[type=checkbox]").locator("visible=true")
        for i in range(boxes.count()):
            if not boxes.nth(i).is_checked():
                boxes.nth(i).check(force=True)
    else:
        for label in labels:
            d.set_checkbox(pg, label, True)
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 1500)


def prepare_play_settings(pg: Page) -> None:
    """The cheapest settings for a probe turn: AI model Lynx, illustrations never.

    Set before Play so the opening turn already uses them (both are per-account menu
    settings, reachable from the world list as well as in game)."""
    set_option(pg, "AI model", "lynx")
    set_option(pg, "Illustration options", "Never")


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
    print("credits after opening:", credits_label(pg))
    (out / "turn1-body.txt").write_text(body(pg))


def take_turn(pg: Page, turn: int, out: Path) -> None:
    pg.locator("textarea").locator("visible=true").first.fill("wait")
    c0 = credits_label(pg)
    t0 = time.time()
    d.vis(pg, 'button:has-text("Take action")').first.click()
    while time.time() - t0 < TURN_TIMEOUT_S:
        pg.wait_for_timeout(1000)
        if d.dialog_text(pg):
            d.close_all_modals(pg, prefer=("OK",))
        if f"turn {turn}" in body(pg) and d.vis(pg, 'button:has-text("Take action")').count():
            break
    else:
        # Seen 2026-11-21: the turn completed but this loop ran to the timeout; the cause is
        # not pinned down yet, so record which half of the test failed.
        seen = f"turn {turn}" in body(pg)
        ready = bool(d.vis(pg, 'button:has-text("Take action")').count())
        print(
            f"turn {turn}: no completion seen in {TURN_TIMEOUT_S}s — 'turn {turn}' in body: "
            f"{seen}, Take action visible: {ready}, dialog: {d.dialog_text(pg)[:80]!r}"
        )
    print(f"turn {turn}: {time.time() - t0:.0f}s, credits {c0!r} -> {credits_label(pg)!r}")
    (out / f"turn{turn}-body.txt").write_text(body(pg))
    (out / f"turn{turn}-debug.txt").write_text(debug_modal(pg))
    (out / f"turn{turn}-items.txt").write_text(tracked_items(pg))


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(exist_ok=True)
    resume = "--resume" in sys.argv[2:]
    with sync_playwright() as pw:
        pg = d.our_page(pw.chromium.connect_over_cdp(d.CDP).contexts[0])
        d.settle_dialogs(pg, 1500)
        prepare_play_settings(pg)
        if not resume:
            start_new_game(pg, out)
        enable_world_debug(pg)
        (out / "turn1-debug.txt").write_text(debug_modal(pg))
        (out / "turn1-items.txt").write_text(tracked_items(pg))
        print("turn1 items:\n" + tracked_items(pg)[:1500])
        for turn in TURNS:
            take_turn(pg, turn, out)
        print("done")


if __name__ == "__main__":
    main()
