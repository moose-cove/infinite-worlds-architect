"""Play Probe F: does a PawScript expression in an extra instruction block re-render from live
tracked-item values on the very next turn after a *player* edits one of those items?

    python play_probe_f.py <outdir> [--manual] [--min-credits N]

Flow (Lynx, illustrations off, every World debug option on — including "Instructions sent
to the AI", which is the definitive evidence):

  1. opening turn (turn 1) and one `wait` turn (turn 2) — View Mode is "A", so every outcome
     should end in PINEAPPLE;
  2. PAUSE. The operator edits View Mode to "B" by hand in the harness tab, through the
     tracked-item editor (toolbar pencil-on-square, `.fa-edit`). While they do, the script
     records what they click (DOM events), every dialog that opens (text + aria snapshot) and
     the Anvil websocket frames the edit sends, so the next harness can do it unattended.
     The pause ends when the Tracked Items panel shows View Mode = B (or `<outdir>/EDIT_DONE`
     exists);
  3. one more `wait` turn (turn 3) — WALRUS on this turn means no lag; PINEAPPLE means the
     block was rendered before the edit (turn lag, same as a trigger).

Re-running resumes from the Probe F turn number shown on screen: the opening turn and any
`wait` turns already played are not replayed. Every turn spends credits (Lynx ran 30–50 per
turn in 2026-09).

The 2026-09-30 run was not driven by this script end to end: the harness opened the game, and
the operator played the rest by hand. Two UI changes seen that day are not handled yet. The
toolbar's editor icon rendered as `.fa-pencil`, not `.fa-edit`. And "World debug tools" only
appears in the menu while Storyteller mode is on (see ../harness/README.md).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import iwdrive as d
import play_probe_d as pd
from playwright.sync_api import Page, sync_playwright

TITLE = "SCHEMA PROBE F - PawScript view switch in instruction block"
pd.TITLE = TITLE
EDIT_WAIT_S = 100 * 60

EVENT_TAP = r"""
() => {
  if (window.__iwxTap) return 'already';
  const ev = window.__iwxEvents = [];
  const t0 = performance.now();
  const desc = (el) => {
    if (!el || !el.tagName) return null;
    const cls = (typeof el.className === 'string' ? el.className : '')
      .split(/\s+/).filter(Boolean).slice(0, 4).join('.');
    const txt = (el.innerText || el.value || '').trim().slice(0, 80);
    return {
      tag: el.tagName.toLowerCase(), id: el.id || null, cls: cls || null,
      role: el.getAttribute('role'), aria: el.getAttribute('aria-label'), title: el.title || null,
      type: el.type || null, text: txt,
      icons: [...el.querySelectorAll('i')].map(i => i.className).join(' | ') || null,
    };
  };
  const path = (el) => {
    const out = [];
    for (let e = el, n = 0; e && e.tagName && n < 8; e = e.parentElement, n++) {
      const cls = (typeof e.className === 'string' ? e.className : '')
        .split(/\s+/).filter(Boolean).slice(0, 3).join('.');
      out.push(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (cls ? '.' + cls : ''));
    }
    return out.join(' < ');
  };
  const modal = (el) => { const m = el.closest && el.closest('.modal'); return m ? m.id : null; };
  const push = (type, e, extra) => ev.push(Object.assign({
    t: Math.round(performance.now() - t0), type, modal: modal(e.target),
    target: desc(e.target), button: desc(e.target.closest && e.target.closest('button')),
    path: path(e.target),
  }, extra || {}));
  document.addEventListener('click', e => push('click', e), true);
  document.addEventListener('focusin', e => push('focusin', e), true);
  // Never record what is typed into a password field (e.g. a re-login during the pause).
  const val = (e) => ({value: e.target.type === 'password'
    ? '<password redacted>' : (e.target.value || '').slice(0, 200)});
  document.addEventListener('change', e => push('change', e, val(e)), true);
  document.addEventListener('input', e => push('input', e, val(e)), true);
  document.addEventListener('keydown', e => {
    if (['Enter', 'Escape', 'Tab'].includes(e.key)) push('keydown', e, {key: e.key});
  }, true);
  window.__iwxTap = true;
  return 'installed';
}
"""


class Recorder:
    """Capture DOM events, dialog appearances and Anvil websocket frames while a human drives."""

    def __init__(self, pg: Page, out: Path):
        self.pg, self.out = pg, out
        self.frames: list[dict] = []
        self.dialogs: list[dict] = []
        self._seen_modals: list[str] = []
        self.t0 = time.time()
        print("event tap:", pg.evaluate(EVENT_TAP))
        self.cdp = pg.context.new_cdp_session(pg)
        self.cdp.send("Network.enable")
        self.cdp.on("Network.webSocketFrameSent", lambda p: self._frame("sent", p))
        self.cdp.on("Network.webSocketFrameReceived", lambda p: self._frame("recv", p))

    def _frame(self, direction: str, p: dict) -> None:
        data = p.get("response", {}).get("payloadData", "")
        self.frames.append(
            {
                "t": round(time.time() - self.t0, 2),
                "dir": direction,
                "len": len(data),
                "data": data[:6000],
            }
        )

    def poll(self) -> None:
        """Call often: snapshot any newly opened modal (text + aria tree)."""
        ids = d.open_modal_ids(self.pg)
        if ids and ids != self._seen_modals:
            top = ids[-1]
            try:
                snap = self.pg.locator(f"#{top}").aria_snapshot()
            except Exception as e:  # noqa: BLE001
                snap = f"<aria snapshot failed: {e}>"
            self.dialogs.append(
                {
                    "t": round(time.time() - self.t0, 2),
                    "modals": ids,
                    "text": d.dialog_text(self.pg)[:6000],
                    "aria": snap[:12000],
                }
            )
            n = len(self.dialogs)
            (self.out / f"edit-dialog-{n}.txt").write_text(
                f"modals={ids}\n\n{self.dialogs[-1]['text']}\n\n---- aria ----\n{snap}"
            )
            print(f"dialog #{n}: {ids} — {self.dialogs[-1]['text'][:80]!r}")
        self._seen_modals = ids

    def dump(self) -> None:
        try:
            events = self.pg.evaluate("() => window.__iwxEvents || []")
        except Exception as e:  # noqa: BLE001
            events = [{"error": str(e)}]
        (self.out / "edit-recording.json").write_text(
            json.dumps({"events": events, "dialogs": self.dialogs, "frames": self.frames}, indent=1)
        )
        lines = [
            f"# {len(events)} DOM events, {len(self.dialogs)} dialogs, "
            f"{len(self.frames)} websocket frames",
            "",
        ]
        for e in events:
            b = e.get("button") or {}
            tg = e.get("target") or {}
            lines.append(
                f"{e.get('t', 0):>7}ms {e.get('type', ''):<8} modal={e.get('modal')} "
                f"target=<{tg.get('tag')} id={tg.get('id')} cls={tg.get('cls')} "
                f"role={tg.get('role')} aria={tg.get('aria')} text={tg.get('text')!r}>"
                + (f" button=<text={b.get('text')!r} icons={b.get('icons')}>" if b else "")
                + (f" value={e.get('value')!r}" if "value" in e else "")
                + (f" key={e.get('key')}" if "key" in e else "")
            )
            lines.append(f"          path: {e.get('path')}")
        lines.append("")
        lines.append("# websocket frames (Anvil):")
        for f in self.frames:
            lines.append(f"{f['t']:>8}s {f['dir']} {f['len']:>6}B {f['data'][:800]!r}")
        (self.out / "edit-recording.txt").write_text("\n".join(lines) + "\n")
        print(
            f"recording: {len(events)} events, {len(self.dialogs)} dialogs, "
            f"{len(self.frames)} frames → {self.out / 'edit-recording.txt'}"
        )


def debug_modal_all(pg: Page) -> str:
    """Open World debug tools (bug icon), expand every collapsible section, return text + aria."""
    pg.locator("button:has(.fa.fa-bug)").locator("visible=true").first.click()
    pg.wait_for_timeout(1500)
    # Headers are toggles, and expanding one can reveal nested ones: click each header text
    # exactly once, re-querying after every click so indices never go stale.
    opened: set[str] = set()
    for _ in range(50):
        hdrs = pg.locator(".modal").locator("visible=true").get_by_text(re.compile(r"\(\d+\)\s*$"))
        todo = None
        for i in range(hdrs.count()):
            h = hdrs.nth(i)
            key = h.inner_text().strip()
            if key not in opened and h.is_visible():
                todo = (key, h)
                break
        if todo is None:
            break
        opened.add(todo[0])
        try:
            todo[1].click(timeout=2000)
            pg.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001 — log and move on; the text dump still runs
            print(f"debug header {todo[0]!r} did not expand: {e}")
    text = d.dialog_text(pg)
    ids = d.open_modal_ids(pg)
    aria = pg.locator(f"#{ids[-1]}").aria_snapshot() if ids else ""
    d.close_all_modals(pg, prefer=("OK",))
    return text + "\n\n---- aria ----\n" + aria


def capture(pg: Page, tag: str, out: Path) -> None:
    (out / f"turn{tag}-body.txt").write_text(pd.body(pg))
    (out / f"turn{tag}-debug.txt").write_text(debug_modal_all(pg))
    (out / f"turn{tag}-items.txt").write_text(pd.tracked_items(pg))
    b = pd.body(pg)
    print(
        f"[{tag}] PINEAPPLE x{b.count('PINEAPPLE')}  WALRUS x{b.count('WALRUS')}  "
        f"credits {pd.credits(pg)}"
    )


def start_game(pg: Page) -> None:
    """Play → Choose character → wait for the opening turn.

    The AI model and illustration options are set beforehand."""
    d.recover(pg)
    row = d.your_world_rows(pg).filter(has_text=TITLE).first
    row.get_by_role("button", name=f'Play "{TITLE}"').first.click()
    pg.wait_for_timeout(1500)
    print("confirm:", d.settle_dialogs(pg, 2000))
    d.wait_for(pg, 'button:has-text("Choose character")', 60000).click()
    popups: list[str] = []
    t0 = time.time()
    while time.time() - t0 < pd.TURN_TIMEOUT_S:
        pg.wait_for_timeout(1000)
        t = d.dialog_text(pg)
        if t:
            popups.append(t[:120].replace("\n", " / "))
            d.close_all_modals(pg, prefer=("OK",))
        if d.vis(pg, 'button:has-text("Take action")').count() and not d.dialog_text(pg):
            break
    print("opening popups:", popups, f"({time.time() - t0:.0f}s)")


def view_mode_is_b(pg: Page) -> bool:
    return re.search(r"View Mode:\s*B\b", pd.body(pg)) is not None


def edit_tracked_item(pg: Page, name: str, value: str, rec: Recorder | None = None) -> None:
    """Player-side edit through the in-game tracked-item editor (toolbar `.fa-edit` icon).

    The dialog lists every player-visible tracked item as a label followed by a textbox, with
    Cancel / OK. Hidden items are not offered. Mapped 2026-09-30 on the 2026-09 UI.
    """
    pg.locator("button:has(.fa.fa-edit)").locator("visible=true").first.click()
    pg.wait_for_timeout(1500)
    if rec:
        rec.poll()
    label = pg.locator(f'.modal :text("{name}")').locator("visible=true").first
    box = label.locator("xpath=following::*[self::input or self::textarea][1]")
    print(f"editor: {name!r} currently {box.input_value()!r} → {value!r}")
    box.fill(value)
    box.press("Tab")
    if rec:
        rec.poll()
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    pg.wait_for_timeout(1500)
    if rec:
        rec.poll()
    print("after OK:", d.settle_dialogs(pg, 3000))


def wait_for_player_edit(pg: Page, out: Path, manual: bool) -> None:
    pd.tracked_items(pg)  # make sure the inline panel is open so the value is on screen
    rec = Recorder(pg, out)
    sentinel = out / "EDIT_DONE"
    sentinel.unlink(missing_ok=True)  # a leftover from an earlier run must not skip the pause
    if manual:
        print(
            "\n=== PAUSED — over to you ===\n"
            f"In the harness tab (title starts '{TITLE[:20]}…'), "
            "use the tracked-item editor to set\n"
            "View Mode to B and confirm. I am recording clicks, dialogs and websocket frames.\n"
            f"Resumes when the Tracked Items panel shows 'View Mode: B' (or touch {sentinel}).\n"
        )
    else:
        edit_tracked_item(pg, "View Mode", "B", rec)
    t0 = time.time()
    seen_b_at = None
    while time.time() - t0 < (EDIT_WAIT_S if manual else 60):
        pg.wait_for_timeout(500)
        rec.poll()
        if sentinel.exists():
            print("sentinel seen")
            break
        if view_mode_is_b(pg) and not d.open_modal_ids(pg):
            seen_b_at = seen_b_at or time.time()
            if time.time() - seen_b_at > 4:  # let the save settle
                print(f"View Mode = B detected after {time.time() - t0:.0f}s")
                break
        else:
            seen_b_at = None
    pg.wait_for_timeout(2000)
    rec.dump()
    # Never spend turn 3 unless the edit really landed: a PINEAPPLE turn after a failed edit
    # would read as "turn lag".
    if not view_mode_is_b(pg):
        raise SystemExit("View Mode is not B after the edit wait; not spending turn 3")


def credits_num(pg: Page) -> float | None:
    c = pd.credits(pg)
    try:
        return float(c.replace(",", ""))
    except ValueError:
        return None


def wait_for_credits(pg: Page, need: float, timeout_s: int = 90 * 60) -> None:
    """Block until the balance shows at least `need` credits (the operator may be topping up in
    another tab meanwhile). Re-reads the top bar every 10 s; a missing balance (tab mid-navigation)
    just keeps waiting."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        c = credits_num(pg)
        if c is not None and c >= need:
            print(f"credits {c:g} >= {need:g}, continuing")
            return
        if c != last:
            print(f"credits {c} < {need:g} — waiting for top-up ({time.time() - t0:.0f}s)")
            last = c
        d.settle_dialogs(pg, 500)
        pg.wait_for_timeout(9500)
    raise SystemExit(f"gave up waiting for {need:g} credits after {timeout_s}s")


def ensure_play_screen(pg: Page) -> None:
    """After a pause the tab may have been reloaded; make sure the play screen is up."""
    for _ in range(30):
        if d.vis(pg, 'button:has-text("Take action")').count() and not d.dialog_text(pg):
            return
        d.settle_dialogs(pg, 1000)
        pg.wait_for_timeout(1000)
    raise SystemExit("play screen not visible — is the harness tab still on the game?")


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(exist_ok=True)
    args = sys.argv[2:]
    # --manual: a human makes the edit in the harness tab; default: the script does.
    manual = "--manual" in args
    # Credit floor per turn (Lynx ran 30–50 per turn in 2026-09). --min-credits sets it for
    # every turn; before turn 2 the script waits for two turns' worth.
    need = float(args[args.index("--min-credits") + 1]) if "--min-credits" in args else 50.0
    with sync_playwright() as pw:
        pg = d.our_page(pw.chromium.connect_over_cdp(d.CDP).contexts[0])
        d.settle_dialogs(pg, 1500)
        print("credits at start:", pd.credits(pg))
        # Resume from whatever state the tab is in: a Probe F game at turn N means the opening
        # (turn 1) and any earlier `wait` turns are already paid for and captured.
        turn = current_turn(pg)
        print("current Probe F turn on screen:", turn)
        if turn is None:
            wait_for_credits(pg, need)
            pd.set_option(pg, "AI model", "lynx", select_label=": Lynx")
            pd.set_option(pg, "Illustration options", "never", select_label="Never")
            start_game(pg)
            turn = 1
        if turn == 1:
            pd.enable_world_debug(pg, labels="all", log_options=out / "debug-options.txt")
            capture(pg, "1", out)
            print(
                "\n=== opening turn done — waiting until the balance covers two more Lynx turns ==="
            )
            wait_for_credits(pg, 2 * need)
            ensure_play_screen(pg)
            pd.take_turn(pg, 2, out)
            capture(pg, "2", out)
            turn = 2
        if turn == 2:
            if view_mode_is_b(pg):
                print("View Mode already B — skipping the edit")
            else:
                wait_for_player_edit(pg, out, manual)
                capture(pg, "2-after-edit", out)
            wait_for_credits(pg, need)
            ensure_play_screen(pg)
            pd.take_turn(pg, 3, out)
            turn = 3
        capture(pg, str(turn), out)
        print("done; credits", pd.credits(pg))


def current_turn(pg: Page) -> int | None:
    """Turn number of the Probe F game on screen, or None if another world / screen is up."""
    m = re.search(r"^SCHEMA PROBE F.*?, turn (\d+)\s*$", pd.body(pg), re.M)
    return int(m[1]) if m else None


if __name__ == "__main__":
    main()
