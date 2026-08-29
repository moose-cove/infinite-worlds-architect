"""Infinite Worlds probe driver. Attaches to the long-lived `iwl browser` Chromium (CDP :9222) and
drives its own tab. Nothing here spends credits except `turn`.

  python iwdrive.py worlds                          list "Your Worlds" titles
  python iwdrive.py export-json --world T out.json  editor → raw JSON → Refresh → save → discard
  python iwdrive.py import-json --world T in.json   editor → raw JSON → paste → Import → Save & exit
  python iwdrive.py snap                            aria snapshot + any open dialog text

Game-play helpers (turns, World Debug, tracked items) live in play_probe_d.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

CDP = "http://127.0.0.1:9222"


# ---------------------------------------------------------------- session


def our_page(ctx) -> Page:
    for pg in ctx.pages:
        try:
            if "infiniteworlds.app" in pg.url and pg.evaluate(
                "() => sessionStorage.getItem('iwx')"
            ):
                return pg
        except Exception:  # noqa: BLE001
            continue
    pg = ctx.new_page()
    pg.goto("https://infiniteworlds.app/", wait_until="domcontentloaded")
    pg.evaluate("() => sessionStorage.setItem('iwx','1')")
    pg.wait_for_timeout(3000)
    return pg


def vis(pg: Page, sel: str):
    return pg.locator(sel).locator("visible=true")


def wait_for(pg: Page, sel: str, timeout=20000):
    vis(pg, sel).first.wait_for(state="visible", timeout=timeout)
    return vis(pg, sel).first


def dialog_text(pg: Page) -> str:
    return pg.evaluate(
        """() => [...document.querySelectorAll('.modal')]
            .filter(e => getComputedStyle(e).display !== 'none').map(e => e.innerText.trim())
            .filter(Boolean).join('\\n---\\n')"""
    )


def dismiss_alert(pg: Page) -> str:
    """Click OK/Yes on any open Bootstrap modal; return its text ('' if none)."""
    txt = dialog_text(pg)
    if txt:
        for label in ("OK", "Yes", "Confirm"):
            b = pg.locator(f'.modal button:has-text("{label}")').locator("visible=true")
            if b.count():
                b.first.click()
                pg.wait_for_timeout(1200)
                break
    return txt


def log(msg: str):
    print(f"[iwdrive] {msg}", file=sys.stderr)


# ---------------------------------------------------------------- navigation


def open_menu(pg: Page):
    wait_for(pg, 'button:has-text("Menu")').click()
    pg.wait_for_timeout(800)


def discard_editor(pg: Page) -> None:
    """Leave the editor without saving (confirms the 'discard all your changes?' prompt)."""
    vis(pg, 'button:has-text("Discard changes")').first.click()
    for _ in range(10):
        pg.wait_for_timeout(400)
        if dialog_text(pg):
            close_all_modals(pg, prefer=("OK",))
            break
    wait_for(pg, 'button:has-text("Back to current adventure")', 30000)
    pg.wait_for_timeout(800)


def goto_world_list(pg: Page):
    close_all_modals(pg, prefer=("OK", "Cancel"))
    if vis(pg, 'button:has-text("Back to current adventure")').count():
        return
    if vis(pg, 'button:has-text("Discard changes")').count():  # in an editor
        discard_editor(pg)
        return
    open_menu(pg)
    wait_for(pg, 'button:has-text("Start new adventure / Edit adventure")').click()
    wait_for(pg, 'button:has-text("Back to current adventure")', 30000)
    pg.wait_for_timeout(1000)


def your_world_rows(pg: Page):
    # "Your Worlds" is the first grid on the list screen (Anvil keeps hidden Edit buttons in the
    # DOM of every row, so filter by grid, not by button presence).
    return pg.locator("[role=grid]").first.locator("[role=row]")


def list_worlds(pg: Page) -> list[str]:
    goto_world_list(pg)
    rows = your_world_rows(pg)
    out = []
    for i in range(rows.count()):
        out.append(rows.nth(i).inner_text().split("\n")[0].strip())
    return out


def open_editor(pg: Page, title: str):
    goto_world_list(pg)
    row = your_world_rows(pg).filter(has_text=title)
    if row.count() == 0:
        raise SystemExit(f"no 'Your Worlds' row matches {title!r}")
    if row.count() > 1:
        log(f"{row.count()} rows match {title!r} (nested row elements?) — using the first")
    row.first.get_by_role("button", name="Edit", exact=True).first.click()
    wait_for(pg, 'button:has-text("Discard changes")', 30000)
    pg.wait_for_timeout(800)


def raw_json_box(pg: Page):
    """From the editor: reveal the raw-JSON textarea; return its locator."""
    cb = pg.locator("input[type=checkbox]").locator("visible=true").first  # Show optional features
    if not cb.is_checked():
        cb.click()
        pg.wait_for_timeout(600)
    if not vis(pg, 'button:has-text("Refresh raw JSON")').count():
        if not vis(pg, 'text="Show raw JSON"').count():
            vis(pg, 'button:has-text("Misc advanced features")').first.click()
            pg.wait_for_timeout(600)
        vis(pg, 'text="Show raw JSON"').first.click()
        wait_for(pg, 'button:has-text("Refresh raw JSON")')
        pg.wait_for_timeout(600)
    box = (
        pg.locator('button:has-text("Refresh raw JSON")')
        .locator("xpath=following::textarea")
        .locator("visible=true")
        .first
    )
    return box


def export_json(pg: Page, title: str, out: Path):
    open_editor(pg, title)
    box = raw_json_box(pg)
    vis(pg, 'button:has-text("Refresh raw JSON")').first.click()
    pg.wait_for_timeout(1000)
    text = box.input_value()
    json.loads(text)  # sanity
    out.write_text(text)
    log(f"exported {len(text)} bytes → {out}")
    discard_editor(pg)


def import_json(pg: Page, title: str, src: Path):
    text = src.read_text()
    json.loads(text)
    open_editor(pg, title)
    box = raw_json_box(pg)
    box.fill(text)
    box.press("Tab")
    vis(pg, 'button:has-text("Import JSON to world")').first.click()
    for _ in range(30):  # the import alert can take a while on a large world
        pg.wait_for_timeout(500)
        if dialog_text(pg):
            break
    d = dialog_text(pg)
    if d:
        log("dialog after import:\n" + d[:1500])
        dismiss_alert(pg)
    # That dismissed the overwrite confirmation. The "World imported from raw JSON."
    # alert arrives up to ~20s AFTER the confirm and intercepts every click until it
    # is closed — poll for it and dismiss before touching the Save button.
    for _ in range(60):
        pg.wait_for_timeout(500)
        d = dialog_text(pg)
        if d:
            log("dialog after confirm: " + d[:200].replace("\n", " / "))
            dismiss_alert(pg)
            if "imported" in d:
                break
    vis(pg, 'button:has-text("Save changes and exit")').first.click()
    for _ in range(30):
        pg.wait_for_timeout(500)
        if dialog_text(pg):
            break
    d = dialog_text(pg)
    if d:
        log("dialog after save:\n" + d[:1500])
    log(
        "import done; now at: "
        + (
            "world list"
            if vis(pg, 'button:has-text("Back to current adventure")').count()
            else pg.url
        )
    )


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--world")
    a = ap.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP)
        pg = our_page(browser.contexts[0])
        if a.cmd == "worlds":
            print("\n".join(list_worlds(pg)))
        elif a.cmd == "export-json":
            export_json(pg, a.world, Path(a.arg))
        elif a.cmd == "import-json":
            import_json(pg, a.world, Path(a.arg))
        elif a.cmd == "recover":
            recover(pg)
        elif a.cmd == "snap":
            print(pg.locator("body").aria_snapshot()[:6000])
            print(dialog_text(pg)[:2000])
        else:
            raise SystemExit("unknown cmd")


def open_modal_ids(pg: Page) -> list[str]:
    return pg.evaluate(
        "() => [...document.querySelectorAll('.modal')]"
        ".filter(e => getComputedStyle(e).display !== 'none').map(e => e.id)"
    )


def close_all_modals(pg: Page, prefer=("Cancel", "OK", "Close")) -> None:
    """Dismiss stacked Bootstrap modals topmost-first (Anvil stacks alert-modal, alert-modal-1…)."""
    for _ in range(6):
        ids = open_modal_ids(pg)
        if not ids:
            return
        top = ids[-1]
        for label in prefer:
            b = pg.locator(f'#{top} button:has-text("{label}")').locator("visible=true")
            if b.count():
                try:
                    b.last.click(timeout=5000)
                except Exception:  # noqa: BLE001 — modal mid-animation / detached; retry next loop
                    pg.wait_for_timeout(700)
                pg.wait_for_timeout(600)
                break
        else:
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(400)


def settle_dialogs(pg: Page, quiet_ms: int = 4000, prefer=("OK",)) -> list[str]:
    """Dismiss dialogs as they appear until none shows up for quiet_ms; return their texts."""
    seen: list[str] = []
    idle = 0
    while idle < quiet_ms:
        t = dialog_text(pg)
        if t:
            seen.append(t[:60].replace("\n", " / "))
            close_all_modals(pg, prefer=prefer)
            idle = 0
        else:
            pg.wait_for_timeout(500)
            idle += 500
    return seen


def recover(pg: Page) -> None:
    """Get back to the world list from any state (reload if needed)."""
    close_all_modals(pg, prefer=("OK", "Cancel"))
    if vis(pg, 'button:has-text("Discard changes")').count():
        discard_editor(pg)
    if not vis(pg, 'button:has-text("Back to current adventure")').count():
        try:
            goto_world_list(pg)
        except Exception:  # noqa: BLE001
            pg.reload(wait_until="domcontentloaded")
            pg.wait_for_timeout(6000)
            pg.evaluate("() => sessionStorage.setItem('iwx','1')")
            settle_dialogs(pg, 2000)
            goto_world_list(pg)


if __name__ == "__main__":
    main()
