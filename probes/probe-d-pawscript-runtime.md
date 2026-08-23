# Probe D — trigger firing and PawScript runtime (build spec)

> **Run 2026-08-22.** Results are recorded in [`README.md` → Answered by Probe D](README.md#answered-by-probe-d-2026-08-22-played);
> the built world is `probe-d-pawscript-runtime.json`, its post-import export
> `probe-d-imported.json`, and the scripts that built and played it are in [`harness/`](harness/README.md).
> One deviation from the spec below: trigger #3 was shipped with `triggerConditions: []`, not an
> absent key, so **Q10 is still open** — see the README.

Closes the questions left open by the 2026-08-22 played rounds recorded under
[Answered in play](README.md#answered-in-play-2026-08-22) in the probes README: the
`triggerOnStartOfGame` variant of P13, the P14/P15 runtime remainders, and the mechanism
behind three findings that were stated as behaviour only (missing-path-in-`or`, comparison
operators in a chance formula, and same-turn state visibility).

**Design:** one world, one import, one *immediate* export, three `wait` turns. Unlike the
two earlier played rounds, every "never fired" result here is interpretable, because the
pre-play export diff tells us whether the condition survived import.

Build it as `probes/probe-d-pawscript-runtime.json`; commit the post-import export as
`probes/probe-d-imported.json`, the same way Probes A and B are kept.

Conventions carried over from the played rounds: white-room world, single PC, `instructions`
that suppress improvisation and forbid tracked-item edits, `updateInstructions: "Never modify
this item…"` on every item, alphanumeric IDs, markers captured in a `visibility: "everyone"`
YAML `Results` item pre-seeded to `"PENDING"`. World Debug → Trigger Event Status open
throughout. Not a publishable world.

---

## Step 0 — settle the round-2 confound (no play, ~2 minutes)

The round-2 world (`pawscript_capability_test_world_v0.2.json`, kept in the
`infinite_worlds_stories` repo under `locked-lesbians/spinoff/`) is already imported.
**Export it now** and run

```
compare_worlds(pawscript_capability_test_world_v0.2.json, <export>)
```

Look only at `triggerConditions` on `TstTC04a`, `TstTC05a`, `TstTP03a`:

| Export shows | Reading |
|---|---|
| condition present, `data` unchanged | runtime-dead: the shape survives and evaluates to never-fire → **docs only**, validator stays at warning |
| `triggerConditions: []` or `data` altered | deleted/rewritten at import → the matching `validate_world` warnings should become errors (same promotion as the legacy-gate rule) |

Record the answer at the top of the results section. This also retroactively fixes the
interpretation of the round-2 missing-path-in-`or` result (`TstTP03a`).

---

## Step 1 — build the world

**Trigger list order is part of the experiment** — author the triggers in exactly this order
and do not let the editor re-sort them.

### Tracked items

| Name | `variableName` | `initialValue` | Notes |
|---|---|---|---|
| Probe | `probe` | `n: 3`<br>`z: 0`<br>`hundred: 100`<br>`flag: 0` | `enforceFormat: true`, schema mirrors the four numeric keys. `flag` is the only field a script writes. |
| Subjects | `subjects` | `amanda:`<br>`  suspicion: 1` | **`enforceFormat: false`** this round — the multi-level and runtime-key creation cells (Q8) would otherwise be confounded by schema enforcement stripping the new shape. |
| Results | `results` | one `"PENDING"` line per marker in the table below | `visibility: "everyone"`, `enforceFormat: false` (scripts create new keys). |

Always-true gate used throughout (proven in the played rounds):

```json
{ "category": "condition", "type": "triggerOnPawScript", "data": "$probe.n > 0" }
```

### Triggers (in list order)

`S:` = `effectRunScript` data. All triggers one-shot unless marked `MORE`
(`canTriggerMoreThanOnce: true`). Markers are written as `$results.<marker> = "FIRED"` unless
a different value is shown.

| # | ID | Question | Conditions / flags | Effect | Marker |
|---|---|---|---|---|---|
| 1 | `PrDSOG01a` | **Q2** SoG, no conditions | `triggerOnStartOfGame: true`, `triggerConditions: []` | `S: $results.sog_empty = "FIRED"` **and** `effectShowMessage: "PROBE SOG-EMPTY"` | `sog_empty` |
| 2 | `PrDSOG02a` | Q2 control: SoG *with* a condition | `triggerOnStartOfGame: true`, gate | same pair, message `"PROBE SOG-GATED"` | `sog_gated` |
| 3 | `PrDABS03a` | **Q10** `triggerConditions` key **absent** (not `[]`) | no `triggerConditions` key at all, no SoG | `S:` marker | `abs_key` |
| 4 | `PrDOR04a` | **Q3** `or` with two valid branches | `"$probe.z > 2 or $probe.n > 2"` | `S:` marker | `or_valid` |
| 5 | `PrDOR05a` | Q3b missing path on the *right* of `or` (round 2 had it on the left) | `"$probe.n > 2 or $subjects.ghost.suspicion > 0"` | `S:` marker | `or_missing_right` |
| 6 | `PrDAND06a` | Q3c `and` | `"$probe.n > 2 and $probe.z < 1"` | `S:` marker | `and_valid` |
| 7 | `PrDIF07a` | **Q4** `if(…)` in a chance formula | `triggerOnRandomChance` `"if($probe.n > 2, 100, 0)"` | `S:` marker | `chance_if` |
| 8 | `PrDBAR08a` | P15b bare `$handle` = 100 | `triggerOnRandomChance` `"$probe.hundred"` | `S:` marker | `chance_bare_100` |
| 9 | `PrDBAR09a` | P15c bare `$handle` = 0 (expect PENDING) | `triggerOnRandomChance` `"$probe.z"` | `S:` marker | `chance_bare_0` |
| 10 | `PrDADD10a` | fixture's additive idiom at runtime | `triggerOnRandomChance` `"$probe.n + 97"` | `S:` marker | `chance_additive` |
| 11 | `PrDTRN11a` | P15d `$game.turn_number` in a chance formula | `triggerOnRandomChance` `"$game.turn_number * 100"` | `S:` marker | `chance_game_turn` |
| 12 | `PrDTRN12a` | fixture's bare `turn_number` at runtime | `triggerOnRandomChance` `"turn_number * 100"` | `S:` marker | `chance_bare_turn` |
| 13 | `PrDPRD13a` | **Q5** producer for the condition-visibility test | gate | `S: $probe.flag = 1` | — |
| 14 | `PrDCND14a` | Q5 consumer — condition reads the same-turn write | `"$probe.flag > 0"` | `S:` marker | `cond_same_turn` |
| 15 | `PrDCNS15a` | **Q6** consumer *before* producer (script order) | gate, **MORE** | `S: $results.order_keys = $subjects.keys().join(",")` | `order_keys` |
| 16 | `PrDPRD16a` | Q6 producer (later in list) | gate | `S: $subjects.late.suspicion = 1` then `$results.late_created = "FIRED"` | `late_created` |
| 17 | `PrDERR17a` | **Q7** errored one-shot | gate | `S: set $x = $subjects.ghost.suspicion` then `$results.err_ran = "FIRED"` | `err_ran` (expect PENDING) |
| 18 | `PrDPRQ18a` | Q7 prereq on the errored trigger | gate + `triggerPrereqs` → `PrDERR17a` (v2.4 object form, `firedThisTurn: false`) | `S:` marker | `prereq_after_error` |
| 19 | `PrDPRQ19a` | Q7 control: prereq on a *succeeding* one-shot | gate + `triggerPrereqs` → `PrDPRD16a` | `S:` marker | `prereq_after_ok` |
| 20 | `PrDDEP20a` | **Q8a** two missing levels | gate | `S: $subjects.deep.stats.trust = 1` then `$results.deep_create = "FIRED"` | `deep_create` |
| 21 | `PrDDYN21a` | **Q8b** create under a runtime key | gate | `S: set $k = "dyn"` / `$subjects.item($k).suspicion = 1` / `$results.dyn_create = "FIRED"` | `dyn_create` |

Run `validate_world` before importing. The only expected warnings are on #1 and #3 (no
conditions — #1 is SoG-exempt under the v0.21.0 rule, so expect #3 only) and possibly on the
`$game.` / bare `turn_number` formulas. Anything else is an authoring error — fix it first.

---

## Step 2 — import, then export **immediately**, then diff

Before any turn is played: import as a new world → export → `compare_worlds(source, export)`.
Record, per trigger, whether its condition survived byte-identical. This column is what makes
every PENDING below readable. Pay special attention to #3 (absent key — does the trigger even
survive?), #5, #7, #11, #12 and #18.

---

## Step 3 — play

Read the opening screen (SoG messages), then **Turn 1 / Turn 2 / Turn 3** with `wait`. After
each turn paste Results, Subjects, and the World Debug trigger list.

---

## Reading the results

| Q | Cell(s) | Decision |
|---|---|---|
| **Q1 confound** | Step 0 | per the Step 0 table |
| **Q2 SoG needs a condition?** | #1 vs #2 | #2 fires & #1 doesn't → SoG with `[]` is dead; the validator warning must **include** SoG triggers and `TRIGGER_EVENTS.md`'s game-start row must say "plus at least one condition". Both fire → the SoG flag is its own gate; keep the exemption. Neither marker but both messages → scripts are no-ops pre-game (use the message as the signal). Neither message nor marker → SoG in this build needs investigating separately. |
| **Q10 absent key** | #3 + Step 2 | present-and-PENDING → same as `[]`; the validator rule already covers absent. Missing from export → import drops the trigger; add to `PLATFORM_BEHAVIOR_NOTES.md`. |
| **Q3 `or`/`and` in conditions** | #4, #5, #6 | #4 fires → `or` works; then the round-2 `TstTP03a` result and #5 isolate "missing path poisons the expression". #5 fires while `TstTP03a` didn't → short-circuit is left-to-right (put the guaranteed branch first). #4 PENDING → `or` is unsupported in conditions; the round-2 mechanism claim was wrong and the fix is "no boolean operators in conditions", not "pre-seed". |
| **Q4 chance formula dialect** | #7–#12 | #7 fires → `if(cond, a, b)` becomes the recommended conditional-odds idiom (over `choose`). #8 fires & #9 stays PENDING → bare `$handle` works and the roll actually uses it. #10 → arithmetic is fine, only comparisons are dead. #11 vs #12 → which `turn_number` spelling the field accepts. A PENDING on any of these with the condition *present* in the Step-2 export is a runtime-dead shape → document as "do not write". |
| **Q5 same-turn write → later condition** | #14 | World Debug "fired turn 1" → conditions see same-turn state. "fired turn 2" → conditions evaluate against start-of-turn state; only scripts see intra-pass writes. |
| **Q6 pass order** | #15 `order_keys` on turn 1 | `"amanda"` → list order confirmed (consumer ran before the later producer). `"amanda,late"` → not list order (or all conditions resolve before any script); document as "visible, order unspecified". Turn 2 must show `late` either way, and turns 2–3 also reveal `deep`/`dyn` from #20/#21. |
| **Q7 errored one-shot & prereqs** | #17, #18, #19 | #19 must fire (prereq mechanics work). Then #18 fires → an errored one-shot still satisfies a prereq; PENDING → it is consumed but does not count as fired for chains. Either result goes into the "rollback is not a retry" text in `PAWSCRIPT.md` §4. |
| **Q8 creation depth / runtime key** | #20, #21, Subjects panel | marker FIRED and the record visible in Subjects → supported; marker PENDING + World Debug problem → rollback, document as unsupported. Check the panel, not just the marker — a "created" record the panel doesn't show is a failure. |

## Deliberately not in this probe

- **Gate cost vs. the ten-`triggerOnEvent` cap** (the P14 runtime remainder). Needs a separate
  world with ten `triggerOnEvent` triggers plus always-true gates; not worth mixing in here.
- **Tracked-item panel timing.** Round 2's `s1_runs: 1` on the turn-1 read already implies
  post-trigger state; #14's World Debug turn number settles what authoring actually needs.
- **P14 import cells** (blank / absent `data`, undeclared `$name`, `<<…>>` in a condition).
  These are import-side and belong in Probe C; keeping them out keeps every trigger here a
  well-formed shape so Step 2's diff stays clean.

Findings land per [After the run](README.md#after-the-run).
