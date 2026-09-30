# Probe harness — driving Infinite Worlds from Playwright

Scripts that run a probe against the live IW app without hand-clicking. They attach to the
long-lived Chromium that `~/personalProjects/iw-likeness` keeps open (`uv run iwl browser`,
CDP on `127.0.0.1:9222`, persistent logged-in profile) and drive **their own tab**, tagged
with `sessionStorage.iwx = "1"`, so an operator's tab is never touched.

| Script | Does | Costs credits? |
|---|---|---|
| `iwdrive.py` | Library + CLI: `worlds`, `export-json --world T out.json`, `import-json --world T in.json`, `recover` (dismiss modals, back to world list from any state), `snap`. Navigates Menu → world list → Edit → "Show optional features" → "Misc advanced features" → "Show raw JSON", and uses the **Refresh raw JSON** (export) / **Import JSON to world** (import) buttons. | No |
| `build_probe_d.py <base.json> <out.json>` | Builds `probes/probe-d-pawscript-runtime.json` from the round-2 white-room world (tracked items and triggers replaced per the build spec). | No |
| `play_probe_d.py <outdir> [--resume]` | Play → Choose character → collect SoG popups → AI model Lynx, illustrations Never → World Debug on → three `wait` turns, saving `turnN-{body,debug,items}.txt`. | Yes — ~21–26 credits per Lynx turn, no images |
| `build_probe_e.py <probe-b-cap.json> <out.json>` | Builds `probes/probe-e-scope-q10.json` (P10-followup scope cells, bogus `recommendedAIModel`, Q10 absent-conditions-key trigger + control). | No |
| `play_probe_e.py <outdir> [--resume]` | Same flow as `play_probe_d.py` (reuses its machinery with the title swapped), two `wait` turns. | Yes — same rates |
| `build_probe_c.py <probe-e-scope-q10.json> <out.json>` | Builds `probes/probe-c-pawscript.json` (six malformed-`triggerOnPawScript` cells, the `firedThisTurn` 2×2 over prereqs and blockers, an undeclared-`$name` chance formula, and a character-scoped item with no per-character entry). | No |
| `play_probe_c.py <outdir> [--resume]` | Same flow again, two `wait` turns — enough to split `firedThisTurn` against a one-shot anchor. | Yes — same rates |
| `build_probe_f.py <probe-e-imported-2.json> <out.json>` | Builds `probes/probe-f-pawscript-view-mode.json`: two `hidden` rule items, a player-edited `View Mode` item, and one EIB that selects a rule with `choose($view_mode, …)`. No triggers. | No |
| `play_probe_f.py <outdir> [--manual] [--min-credits N]` | Opening turn, one `wait` turn, then a pause while `View Mode` is edited to `B`. The script makes the edit itself, or with `--manual` records how the operator does it (DOM events, dialogs, websocket frames). Then one more `wait`. It waits for the credit balance to cover each turn and resumes from the on-screen turn number. **Not yet updated for the 2026-09-30 UI** (see below); the Probe F result was played by hand. | Yes — Lynx ran 30–50 per turn in 2026-09 |

Run with the iw-likeness environment, which already has Playwright installed:

```bash
uv run --project ~/personalProjects/iw-likeness python probes/harness/iwdrive.py worlds
```

The Claude Code Bash sandbox blocks loopback, so every invocation needs the sandbox
disabled (`dangerouslyDisableSandbox`) or to be run from a plain terminal.

## UI facts the driver depends on

- IW is a single-URL Anvil app. Dialogs are stacked Bootstrap modals (`#alert-modal`,
  `#alert-modal-1`, …); detect them by `getComputedStyle(el).display !== "none"` — fixed-position
  modals have `offsetParent === null`, so the usual visibility test lies.
- "Your Worlds" is the **first** `[role=grid]` on the list screen. Every row keeps hidden
  Play/Edit/Make copy/Share/Delete buttons in the DOM, so scope to the grid and use
  `get_by_role("button", name="Edit", exact=True)`.
- Import flow: paste → **Import JSON to world** → "Are you sure you wish to overwrite…" → OK →
  "World imported from raw JSON." The import **persists immediately**; **Save changes and
  exit** afterwards reports "No changes to save." **Discard changes** asks for confirmation.
- The import alert can arrive 10–20 s after the click on a large world — poll, don't sleep.
  Sequence: overwrite confirmation first, then (after the OK, up to ~20 s later) the
  "World imported from raw JSON." alert, which intercepts every click until dismissed —
  `import_json` polls for and dismisses both before touching **Save changes and exit**.
- Play screen: `textarea` + **Take action**; toolbar icons `.fa-database` (inline Tracked
  Items panel) and `.fa-bug` (World debug tools modal with collapsible "Triggers (N)" /
  "PawScript (N)" sections, per-trigger error text and **Open in Sandbox** links).
- Menu → **AI model** radios (`smilodon`, `lynx`, …) and **Illustration options** radios
  (`always` / `on_change` / `never`). Smilodon with an image ran 33–38 credits per turn; Lynx
  without images 21–26.
- **2026-09 UI refresh.** The menu is now `role=menuitem` entries: World Browser, Load game,
  AI model, and a **Settings** submenu (Storyteller mode, Illustration options, Keep menu bar
  on screen). `iwdrive.menu_click` / `menu_path` try the menuitem first, then the legacy
  button. Illustration options is now a `<select>`. The credits button's `aria-label` reads
  `"N credits, X of Y free turns left today"`. Lynx is free for 3 turns a day on the test
  account.
- **"World debug tools" only appears (under Settings) while Storyteller mode is on.**
  `play_probe_d.enable_world_debug` does not switch Storyteller mode on yet. Turn it on by hand,
  or the call fails with "no menu entry".
- The in-game toolbar icons on 2026-09-30 were `.fa-user`, `.fa-database`, `.fa-pencil`,
  `.fa-meh-o`. `play_probe_f.edit_tracked_item` still looks for `.fa-edit` (the tracked-item
  editor when it was mapped earlier the same day). Confirm the pencil opens the same editor
  before automating the edit again.
- The top row of the world list can sit under `.iw-top-bar-overlay`, which intercepts real
  pointer clicks. `iwdrive.open_editor` therefore fires the row's Edit button with
  `dispatch_event("click")`.
- **Test account.** The harness Chromium profile is logged into a dedicated throwaway IW
  account, not a personal one. Its credentials live in `probes/test-account.env`, which is
  gitignored and must never be committed. A fresh account has no Your Worlds rows, and
  "Create your own adventure" only offers AI generation. To get an importable slot, use
  **Make copy** on an example world, then `import-json` over the copy.
- The **PawScript Expression Sandbox** (from any Open in Sandbox link) is a CodeMirror editor
  (`.cm-editor .cm-content`) with an **Evaluate** button; it evaluates against the real turn's
  data and costs nothing — use it before spending a turn on a condition.

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
