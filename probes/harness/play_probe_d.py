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
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

TITLE = "Probe D - PawScript runtime"
TURNS = (2, 3, 4)  # turn 1 is the opening IW generates at game start
TURN_TIMEOUT_S = 240
# A turn is complete once the narrative has changed and then stayed the same for this many
# consecutive 1 s polls (with Take action back and no dialog open).
STABLE_POLLS = 3
# Dialogs OK'd while a turn runs: the probe worlds' own effectShowMessage popups, which all
# start "PROBE …". Anything else (a credits prompt, an error, "Session Expired") stops the
# run instead of being clicked away.
TURN_DIALOG_OK = re.compile(r"\bPROBE\b")


class TurnTimeout(RuntimeError):
    """A turn (or the opening turn) did not visibly complete within TURN_TIMEOUT_S. Raised so
    no caller writes a half-finished turn's captures as complete or spends the next turn."""


class UnexpectedDialog(RuntimeError):
    """A dialog other than a probe world's own message popped up while a turn ran."""


class DebugSectionsCollapsed(RuntimeError):
    """World debug tools sections were still collapsed after every header had been tried."""


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
    print("warning: credits balance not found in the top bar; reporting '?'")
    return "?"


def credits_label(pg: Page) -> str:
    """The credits button's full aria-label (balance plus free turns left), for logs."""
    b = pg.locator('button[aria-label*=" credits"]').locator("visible=true")
    label = b.first.get_attribute("aria-label") if b.count() else None
    if not label:
        print("warning: credits button not found in the top bar; reporting '?'")
    return label or "?"


# The turn's AI-suggested actions: buttons with a leading right-arrow icon. "Take action"
# carries the same icon, so it is filtered out by text.
SUGGESTION_BUTTON = "button:has(i.fa-arrow-right)"


def tracked_items(pg: Page) -> str:
    """Open the inline Tracked Items panel and return its text.

    The toolbar database icon ("Show information on tracked items") is a toggle and the
    panel can render a beat after the click, so poll for its header, and click again only
    if it never appears. The panel sits straight above the suggested-action buttons, so the
    text is cut at the first suggestion's label (whatever this turn's suggestions are), or
    at "Or type any action you want below:" when no suggestion is showing."""
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
    sugg = pg.locator(SUGGESTION_BUTTON).locator("visible=true").filter(has_not_text="Take action")
    ends = [sugg.first.inner_text().strip()] if sugg.count() else []
    ends.append("Or type any action you want below:")
    for end in ends:
        if end and end in seg:
            seg = seg.split(end, 1)[0]
            break
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
    have content. "Triggers" and "PawScript" headers carry a count when non-empty
    ("Triggers (3)", "PawScript (5)"). Expanding one can reveal nested collapsed headers, so
    keep clicking collapsed headers until none is left. Each header (keyed by its text) is
    clicked at most once, so one whose chevron never flips cannot starve the rest; a failed
    click is logged and skipped. Raises DebugSectionsCollapsed (after closing the modal) if
    any section is still collapsed at the end, rather than return half-expanded content.
    """
    pg.locator("button:has(.fa.fa-bug)").locator("visible=true").first.click()
    pg.wait_for_timeout(1500)
    ids = d.open_modal_ids(pg)
    if not ids:
        raise RuntimeError("World debug tools modal did not open")
    modal = pg.locator(f"#{ids[-1]}")
    handled: set[str] = set()
    for _ in range(60):
        hdrs = modal.locator(COLLAPSED_SECTION).locator("visible=true")
        todo = None
        for i in range(hdrs.count()):
            key = hdrs.nth(i).inner_text().strip()
            if key not in handled:
                todo = (hdrs.nth(i), key)
                break
        if todo is None:
            break
        hdr, key = todo
        handled.add(key)
        try:
            hdr.click(timeout=5000)
        except PlaywrightError as e:
            print(f"open_debug_modal: clicking {key!r} failed: {str(e).splitlines()[0]}")
        pg.wait_for_timeout(500)
    left = modal.locator(COLLAPSED_SECTION).locator("visible=true").all_inner_texts()
    if left:
        d.close_all_modals(pg, prefer=("OK",))
        raise DebugSectionsCollapsed(
            f"World debug tools: sections still collapsed after trying each once: {left!r}"
        )
    return ids[-1]


def debug_modal(pg: Page) -> str:
    """Open World debug tools, expand every section, return the modal text and close it."""
    open_debug_modal(pg)
    t = d.dialog_text(pg)
    d.close_all_modals(pg, prefer=("OK",))
    return t


SANDBOX_TIMEOUT_S = 20


def _sandbox_output(text: str) -> str:
    """The sandbox's evaluation output: the text between its Share and Update Game buttons
    ('' before Evaluate has produced anything). A value reads "Result / does this condition
    fire / …"; an error is the bare message ("No tracked item or variable called 'x'."),
    with no "Result" line."""
    i = text.rfind("\nShare\n")
    if i < 0:
        return ""
    j = text.find("\nUpdate Game", i)
    return (text[i + len("\nShare\n") : j] if j >= 0 else "").strip()


def _close_sandbox(pg: Page, sb) -> None:
    sb.get_by_role("button", name="Close", exact=True).click()
    pg.wait_for_timeout(1000)
    d.close_all_modals(pg, prefer=("OK",))


def sandbox_eval(pg: Page, trigger: str, expr: str) -> str:
    """Evaluate `expr` in the in-game PawScript Expression Sandbox, opened from the World
    debug tools PawScript entry for trigger `trigger`; return the evaluation output (see
    `_sandbox_output`). Free: it evaluates against the turn's data without playing a turn.

    The sandbox is a second stacked modal (CodeMirror expression box, Evaluate, Share,
    Update Game, Close). Only Evaluate and Close are touched — never "Update Game". Raises
    RuntimeError if the sandbox does not open, the expression box does not read back `expr`
    after typing, or no output appears within SANDBOX_TIMEOUT_S of Evaluate."""
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
    n_open = len(d.open_modal_ids(pg))
    pg.locator(f"#{top}").get_by_text("Open in Sandbox", exact=True).nth(nth).click()
    for _ in range(20):
        pg.wait_for_timeout(500)
        if len(d.open_modal_ids(pg)) > n_open:
            break
    else:
        d.close_all_modals(pg, prefer=("OK",))
        raise RuntimeError(f"Expression Sandbox did not open for {trigger!r}")
    pg.wait_for_timeout(1000)
    sb = pg.locator(f"#{d.open_modal_ids(pg)[-1]}")
    box = sb.locator(".cm-editor .cm-content").locator("visible=true").last
    box.click()
    pg.keyboard.press("Control+A")
    pg.keyboard.type(expr)
    typed = box.inner_text()
    if " ".join(typed.split()) != " ".join(expr.split()):
        _close_sandbox(pg, sb)
        raise RuntimeError(f"sandbox expression box reads {typed!r}, not {expr!r}")
    sb.get_by_role("button", name="Evaluate", exact=True).click()
    deadline = time.monotonic() + SANDBOX_TIMEOUT_S
    result = ""
    while not result and time.monotonic() < deadline:
        pg.wait_for_timeout(500)
        result = _sandbox_output(sb.inner_text())
    _close_sandbox(pg, sb)
    if not result:
        raise RuntimeError(f"sandbox: no output for {expr!r} within {SANDBOX_TIMEOUT_S}s")
    return result


MENU_PATHS = {
    "AI model": ("AI model",),
    "Illustration options": ("Settings", "Illustration options"),
    "World debug tools": ("Settings", "World debug tools"),
}


def open_option(pg: Page, menu_item: str) -> None:
    """Open the dialog behind a menu option (see MENU_PATHS for where each one lives)."""
    d.menu_path(pg, *MENU_PATHS.get(menu_item, (menu_item,)))
    pg.wait_for_timeout(1200)


def _option_control(pg: Page, menu_item: str, value: str):
    """In the open option dialog: ("radio", locator) for a radio whose value is `value`, else
    ("select", locator) for the one visible <select> offering an option labelled `value`."""
    radio = pg.locator(f".modal input[type=radio][value={value}]")
    if radio.count():
        return "radio", radio.first
    sel = (
        pg.locator(".modal select")
        .locator("visible=true")
        .filter(has=pg.locator(f'option:text-is("{value}")'))
    )
    if sel.count() != 1:
        raise SystemExit(f"{menu_item}: no radio {value!r} and {sel.count()} selects offer it")
    return "select", sel.first


def set_option(pg: Page, menu_item: str, value: str) -> None:
    """Menu → <menu_item> → pick `value` → OK, then re-open the dialog and check it stuck.

    "AI model" is a radio group (`value` is the radio's value, e.g. "lynx"). "Illustration
    options" holds two <select>s ("Automatically generate images", "Alternative images per
    turn"); `value` is an option label ("Never") and picks the select that offers it.
    Raises RuntimeError if the re-opened dialog shows another value — a rejected model change
    would otherwise leave the account on a dearer model for every later turn."""
    open_option(pg, menu_item)
    kind, ctl = _option_control(pg, menu_item, value)
    if kind == "radio":
        ctl.check(force=True)
    else:
        ctl.select_option(label=value)
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 2000)
    open_option(pg, menu_item)
    kind, ctl = _option_control(pg, menu_item, value)
    if kind == "radio":
        got = pg.locator(".modal input[type=radio]:checked").first.get_attribute("value")
    else:
        got = ctl.evaluate("s => s.options[s.selectedIndex] && s.options[s.selectedIndex].text")
    d.close_all_modals(pg, prefer=("Cancel",))
    if got != value:
        raise RuntimeError(f"{menu_item}: set {value!r} but the dialog reads {got!r} afterwards")
    print(f"{menu_item}: {value!r} (read back)")


WORLD_DEBUG_DEFAULT = ("Trigger status", "PawScript (scripts, conditions and the Sandbox)")


def enable_world_debug(
    pg: Page, labels=WORLD_DEBUG_DEFAULT, log_options: Path | None = None
) -> None:
    """Tick the given World debug tools checkboxes (by exact label). `labels="all"` ticks
    every visible checkbox in the dialog; `log_options` saves the dialog text (the option list).

    The menu entry only exists while Storyteller mode is on (Menu → Settings → Storyteller
    mode). This does not switch it on; it fails with a pointer to it instead. After OK it
    re-opens the dialog and raises RuntimeError if a requested box is unticked (for "all":
    any visible, enabled box)."""
    try:
        open_option(pg, "World debug tools")
    except d.MenuEntryMissing as e:
        raise SystemExit(f"{e} — turn on Storyteller mode (Menu → Settings) and re-run") from e
    if log_options:
        log_options.write_text(d.dialog_text(pg))
    boxes = pg.locator(".modal input[type=checkbox]").locator("visible=true")
    if labels == "all":
        for i in range(boxes.count()):
            if not boxes.nth(i).is_checked():
                boxes.nth(i).check(force=True)
    else:
        for label in labels:
            d.set_checkbox(pg, label, True)
    pg.locator('.modal button:has-text("OK")').locator("visible=true").last.click()
    d.settle_dialogs(pg, 1500)
    open_option(pg, "World debug tools")
    if labels == "all":
        unticked = [
            boxes.nth(i).evaluate("e => (e.closest('label') || e).innerText.trim()")
            for i in range(boxes.count())
            if boxes.nth(i).is_enabled() and not boxes.nth(i).is_checked()
        ]
    else:
        unticked = [lb for lb in labels if not d.labelled_checkbox(pg, lb).is_checked()]
    d.close_all_modals(pg, prefer=("OK",))  # the dialog has no Cancel; nothing changed
    if unticked:
        raise RuntimeError(f"World debug tools: still unticked after OK: {unticked!r}")
    print("World debug tools: requested options ticked (read back)")


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
    while True:
        if time.time() - t0 > TURN_TIMEOUT_S:
            raise TurnTimeout(
                f"opening turn: no play screen within {TURN_TIMEOUT_S}s; popups {opening!r}"
            )
        pg.wait_for_timeout(1000)
        t = d.dialog_text(pg)
        if t:
            opening.append(t[:120].replace("\n", " / "))
            d.close_all_modals(pg, prefer=("OK",))
        if take_action_ready(pg) and not d.dialog_text(pg):
            break
    print("opening popups:", opening)
    print("credits after opening:", credits_label(pg))
    (out / "turn1-body.txt").write_text(body(pg))


def narrative(pg: Page) -> str:
    """The page text minus its first line, the play header ("<world> - <character>, turn
    N"), whose turn number can lag well behind a finished turn."""
    return body(pg).split("\n", 1)[-1]


def take_action_ready(pg: Page) -> bool:
    b = d.vis(pg, 'button:has-text("Take action")')
    return bool(b.count()) and b.first.is_enabled()


def take_turn(pg: Page, turn: int, out: Path) -> None:
    """Play one `wait` turn and save turn<N>-{body,debug,items}.txt.

    Completion is not read from the header: on 2026-11-21/22 it still said the previous turn
    number long after the new narrative was complete and Take action was back. The turn
    counts as complete once the narrative (page text minus the header line) differs from
    before the click, has been unchanged for STABLE_POLLS consecutive 1 s polls, Take action
    is visible and enabled, and no dialog is open. A header that does not read "turn N" then
    is only logged. Probe popups (TURN_DIALOG_OK) are logged and OK'd; any other dialog
    raises UnexpectedDialog, and no completion within TURN_TIMEOUT_S raises TurnTimeout —
    either way nothing is captured and the caller's next turn is never spent."""
    before = narrative(pg)
    pg.locator("textarea").locator("visible=true").first.fill("wait")
    c0 = credits_label(pg)
    t0 = time.time()
    d.vis(pg, 'button:has-text("Take action")').first.click()
    last, stable = None, 0
    while True:
        if time.time() - t0 > TURN_TIMEOUT_S:
            raise TurnTimeout(
                f"turn {turn}: no completion in {TURN_TIMEOUT_S}s — narrative changed: "
                f"{narrative(pg) != before}, stable polls: {stable}, Take action ready: "
                f"{take_action_ready(pg)}, dialog: {d.dialog_text(pg)[:120]!r}"
            )
        pg.wait_for_timeout(1000)
        dlg = d.dialog_text(pg)
        if dlg:
            print(f"turn {turn}: dialog during turn: {dlg[:300]!r}")
            if not TURN_DIALOG_OK.search(dlg):
                raise UnexpectedDialog(f"turn {turn}: unexpected dialog, left open: {dlg[:300]!r}")
            for c in d.close_all_modals(pg, prefer=("OK",)):
                print(f"turn {turn}: dismissed {c!r}")
            last, stable = None, 0
            continue
        now = narrative(pg)
        stable = stable + 1 if now == last else 1
        last = now
        if now != before and stable >= STABLE_POLLS and take_action_ready(pg):
            break
    header = body(pg).split("\n", 1)[0]
    if not re.search(rf",\s*turn {turn}\s*$", header):
        print(f"turn {turn}: complete, but the header still reads {header!r}")
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
