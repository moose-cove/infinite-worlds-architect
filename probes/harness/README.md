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
