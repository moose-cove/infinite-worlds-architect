# Probe harness — driving Infinite Worlds from Playwright

Scripts that run a probe against the live IW app without hand-clicking. They attach to the
long-lived Chromium that `~/personalProjects/iw-likeness` keeps open (`uv run iwl browser`,
CDP on `127.0.0.1:9222`, persistent logged-in profile) and drive **their own tab**, tagged
with `sessionStorage.iwx = "1"`, so an operator's tab is never touched.

| Script | Does | Costs credits? |
|---|---|---|
| `iwdrive.py` | Library + CLI: `worlds`, `export-json --world T out.json`, `import-json --world T in.json`, `recover` (dismiss modals, back to world list from any state), `snap`. Navigates Menu → world list → Edit → "Show optional features" → "Misc advanced features" → "Show raw JSON", and uses the **Refresh raw JSON** (export) / **Import JSON to world** (import) buttons. | No |
| `build_probe_d.py <base.json> <out.json>` | Builds `probes/probe-d-pawscript-runtime.json` from the round-2 white-room world (tracked items and triggers replaced per the build spec). | No |
| `play_probe_d.py <outdir> [--resume]` | AI model Lynx, illustrations Never → Play → Choose character → collect SoG popups → World Debug on → three `wait` turns, saving `turnN-{body,debug,items}.txt`. Also holds the shared helpers (`open_debug_modal`, `sandbox_eval`, `tracked_items`, `set_option`, …). | Yes — Lynx 30–50 credits per turn after the daily free turns, no images |
| `build_probe_e.py <probe-b-cap.json> <out.json>` | Builds `probes/probe-e-scope-q10.json` (P10-followup scope cells, bogus `recommendedAIModel`, Q10 absent-conditions-key trigger + control). | No |
| `play_probe_e.py <outdir> [--resume]` | Same flow as `play_probe_d.py` (reuses its machinery with the title swapped), two `wait` turns. | Yes — same rates |
| `build_probe_c.py <probe-e-scope-q10.json> <out.json>` | Builds `probes/probe-c-pawscript.json` (six malformed-`triggerOnPawScript` cells, the `firedThisTurn` 2×2 over prereqs and blockers, an undeclared-`$name` chance formula, and a character-scoped item with no per-character entry). | No |
| `play_probe_c.py <outdir> [--resume]` | Same flow again, two `wait` turns — enough to split `firedThisTurn` against a one-shot anchor. | Yes — same rates |
| `build_probe_f.py <probe-e-imported-2.json> <out.json>` | Builds `probes/probe-f-pawscript-view-mode.json`: two `hidden` rule items, a player-edited `View Mode` item, and one EIB that selects a rule with `choose($view_mode, …)`. No triggers. | No |
| `play_probe_f.py <outdir> [--manual] [--min-credits N]` | Opening turn, one `wait` turn, then a pause while `View Mode` is edited to `B`. The script makes the edit itself, or with `--manual` records how the operator does it (DOM events, dialogs, websocket frames). Then one more `wait`. It waits for the balance to cover each turn (`--min-credits`, default 50, doubled before turn 2), refuses to spend turn 3 unless `View Mode` really reads `B`, and resumes from the on-screen turn number. Needs Storyteller mode on. The Probe F result itself was played by hand. | Yes — Lynx 30–50 per turn after the daily free turns |

Run with the iw-likeness environment, which already has Playwright installed:

```bash
uv run --project ~/personalProjects/iw-likeness python probes/harness/iwdrive.py worlds
```

The Claude Code Bash sandbox blocks loopback, so every invocation needs the sandbox
disabled (`dangerouslyDisableSandbox`) or to be run from a plain terminal.

## UI facts the driver depends on

Re-mapped live on **2026-11-21** (no app version string is exposed in the UI; the page is the
same single-URL Anvil app). Older layouts are not supported.

- IW is a single-URL Anvil app. Dialogs are stacked Bootstrap modals (`#alert-modal`,
  `#alert-modal-1`, …); detect them by `getComputedStyle(el).display !== "none"` — fixed-position
  modals have `offsetParent === null`, so the usual visibility test lies.
- **Menu.** The top-bar **Menu** button opens a `role=menu` of `role=menuitem` entries: World
  Browser, the ongoing game(s), Save game, Load game, Restart game, Image style, AI model,
  Export story, Comic Maker, and a **Settings** submenu (Storyteller mode, World debug tools,
  Illustration options, Keep menu bar on screen). Entries carry a second line ("AI model /
  LYNX"), so `iwdrive.menu_click` / `menu_path` match by partial name. The legacy
  button-menu fallbacks are gone.
- **"World debug tools" only appears under Settings while Storyteller mode is on.**
  `play_probe_d.enable_world_debug` does not switch Storyteller mode on; without it the call
  stops with a pointer to the setting. Its dialog's checkboxes are matched by exact label
  (`iwdrive.set_checkbox`): "Instructions sent to the AI", "Trigger status", "AI thinking and
  evaluation", "Long term memory (games started on the new memory system)", "Include
  "Extra-hidden" tracked items in "Hidden tracked items" view", "PawScript (scripts,
  conditions and the Sandbox)", plus a hidden "Show "auto-succeed" checkbox on action bar".
- **AI model** is a radio group (`value` = `lynx`, `dolphin`, …; Dolphin is the account
  default). **Illustration options** holds two `<select>`s, "Automatically generate images"
  (Every turn / When the illustration subject changes / Never) and "Alternative images per
  turn"; `set_option` picks the select that offers the requested label. Both are account
  settings and can be set from the world list, so `prepare_play_settings` sets Lynx +
  Never **before** Play and the opening turn already uses them.
- **Credits.** The credits button's `aria-label` reads `"N credits, X of Y free turns left
  today"`. On 2026-11-21 Lynx gave the test account 3 free turns a day (the AI model dialog
  quotes 30–50 credits per Lynx turn after that); a free turn leaves the balance unchanged.
- **World list.** "Your Worlds" is the **first** `[role=grid]` on the list screen, now a
  Tabulator table: its hidden header (`.tabulator-headers`, text "uuid") is also a
  `role=row`, so `your_world_rows` selects `.tabulator-row`. Every row keeps hidden
  Play/Edit/Make copy/Share/Delete buttons in the DOM, so scope to the grid and use
  `get_by_role("button", name="Edit", exact=True)`. Two worlds may share a title; `--world`
  takes the first matching row.
- The top row of the world list can sit under `.iw-top-bar-overlay`, which intercepts real
  pointer clicks. `iwdrive.open_editor` therefore fires the row's Edit button with
  `dispatch_event("click")`.
- **Never pick an editor checkbox by position.** "Show optional features" is the editor's
  last checkbox in DOM order. With a trigger card expanded, the first visible checkbox is
  that trigger's "Trigger at start of game". `iwdrive.labelled_checkbox` / `set_checkbox`
  match the checkbox by its exact `<label>` text and set it by state, never by a blind
  click. `raw_json_box` uses them for both "Show optional features" and "Show raw JSON"
  (under "Misc advanced features (optional)").
- **Import flow:** paste → **Import JSON to world** → "Are you sure you wish to overwrite…" →
  OK → "World imported from raw JSON." → OK → **Save changes and exit**, which reports
  "Changes saved!" or "No changes to save." (both seen on 2026-11-21) — OK that too. The
  imported alert arrived **over 35 s** after the confirm for Probe C's 12-trigger world.
  Saving before it arrives saves the editor's pre-import state over the import (seen
  2026-11-21: the old 30 s wait lost an import), so `import_json` waits up to
  `IMPORT_TIMEOUT_S` (180 s) for it and raises rather than save without it. After an
  import the editor re-renders with the raw-JSON section hidden again.
- **Discard changes** asks for confirmation when the editor holds unsaved changes ("Are you
  sure you wish to discard all your changes to this world?"), and may then show a "Changes
  discarded." alert that hides the world list until it is OK'd. That alert has arrived more
  than 4 s after the confirm, so `discard_editor` polls for it for up to 30 s. With no
  changes (a plain export) it shows neither.
- **Starting a game:** the row's `Play "<title>"` button → "Your current game is safe / You'll
  find it under Ongoing games" (when a game is open) → **Choose character** → the world's
  start popup(s) → the play screen (`textarea` + **Take action**). The play header reads
  `<world title> - <character>, turn N`.
- **In-game toolbar** (icon class → tooltip): `.fa-user` Show details of your character,
  `.fa-database` Show information on tracked items (inline toggle panel headed "Tracked
  Items", can render a beat after the click), `.fa-lock` Show hidden tracked items,
  `.fa-edit` **Edit tracked items (Storyteller mode only)**, `.fa-bug` World debug tools,
  `.fa-eye` Reveal secret information for this turn (Storyteller mode only), `.fa-pencil`
  Edit text for this turn (Storyteller mode only), `.fa-meh-o` Rate this turn. The
  tracked-item editor is `.fa-edit`, not the pencil.
- **Tracked-item editor** (`play_probe_f.edit_tracked_item`): a modal listing each item as a
  label followed by a `<textarea>`, with Cancel / OK. On 2026-11-21 (Storyteller mode on,
  every debug option ticked) it offered `hidden` items too. After an edit the play screen
  shows a "Show changes" link.
- **World debug tools modal** (bug icon): a stack of collapsible section buttons, all
  collapsed on open — "Active instructions" (nested "Main instructions" and one entry per
  active extra instruction block), "Triggers (N)" ("Triggers fired this turn" / "All
  triggers"), "Evaluation", "PawScript (N)", and "Inactive instructions", "Model thinking",
  "Long term memory" when those have content. The "(N)" count appears only when the section
  is non-empty. A collapsed header's leading icon is `.fa-angle-right` (`.fa-angle-down` once
  open); `play_probe_d.open_debug_modal` clicks collapsed headers until none is left. The
  footer has a **Replay this turn** link — never click it.
- **PawScript Expression Sandbox.** Each condition entry in the debug modal's PawScript
  section ("Trigger:" / name / "PawScript condition" / **Open in Sandbox** / result) opens
  the sandbox as a second stacked modal: the turn's real data (editable, "data changes are
  not saved"), a CodeMirror expression box (`.cm-editor .cm-content`), **Evaluate**,
  **Share**, **Update Game** and **Close**. It costs nothing — use it before spending a turn
  on a condition. `play_probe_d.sandbox_eval(pg, trigger, expr)` drives it (Evaluate and
  Close only, never Update Game).
- **Test account.** The harness Chromium profile is logged into a dedicated throwaway IW
  account, not a personal one. Its credentials live in `probes/test-account.env`, which is
  gitignored and must never be committed. A fresh account has no Your Worlds rows, and
  "Create your own adventure" only offers AI generation. To get an importable slot, use
  **Make copy** on an example world, then `import-json` over the copy.
- **Turn-complete detection is unconfirmed on this UI.** `take_turn` waits for "turn N" in
  the page text plus a visible **Take action**. On 2026-11-21 the one `wait` turn played
  completed (debug modal and tracked items captured for turn 2), but the loop ran to its
  240 s timeout first; it now logs which half of the test failed when that happens.

## Probe D evidence kept here

`probe-d-turn1-debug.txt` / `probe-d-turn4-debug.txt` are the World Debug modal after the
opening turn and after the third `wait`; `probe-d-turn4-items.txt` is the final tracked-items
panel; `probe-d-sandbox-results.txt` is the Expression Sandbox transcript (run on the round-2
world at turn 2). Results are read out in [`../README.md`](../README.md#answered-by-probe-d-2026-08-22-played).

## Probe E evidence kept here

`probe-e-turn1-debug.txt` / `probe-e-turn3-debug.txt` are the World Debug modal after the
opening turn and after the second `wait` (control fired every turn; the Q10 absent-key
trigger "not yet fired" throughout); `probe-e-turn3-items.txt` is the final tracked-items
panel. The round-trip evidence is `../probe-e-imported.json` and `../probe-e-imported-2.json`.
Results are read out in
[`../README.md`](../README.md#answered-by-probe-e-2026-08-28-two-round-trips--played).

## Probe C evidence kept here

`probe-c-turn1-debug.txt` / `probe-c-turn3-debug.txt` are the World Debug modal after the
opening turn and after the second `wait`. Read them together for `firedThisTurn`: turn 1 shows
the anchor plus both prereq cells firing and both blocker cells silent; turn 3's "All triggers"
list separates them (`P2a … fired turn 1` alone, `P2b … fired 3 times`, `P2c … first fired
turn 2`, `P2d … not yet fired`). The same modals carry the per-cell PawScript errors for P14b,
P14d, P14e, P14f and the P15 rider — including `Lemon = "Lemon"`, which is what `<<…>>`
interpolation compiles to. Note P14c (absent `data`) appears in neither panel, which is the
only signal distinguishing it from P14b. `probe-c-turn3-items.txt` confirms the seeded value is
live in play; the auto-created entry itself is visible in the export,
`../probe-c-imported.json`. Results are read out in
[`../README.md`](../README.md#answered-by-probe-c-2026-08-29-round-trip--played).
