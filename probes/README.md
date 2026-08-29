# Schema probes

Instrument worlds for the schema v2.4 questions the plugin currently answers with
"unverified". Each probe is a deliberately minimal world whose only job is to make the
platform reveal a behaviour we cannot read out of the schema, the canonical fixture, or
the wiki.

| File | Covers | Status |
|---|---|---|
| `probes/probe-a-core.json` | Gate-condition shapes, `firedThisTurn`, the `conditions` registry, `hidden_boring`, `not_equal`, nested YAML, image-style precedence, menu-backed `initialPCValue` | **Round trip run** — see [Recorded results](#recorded-results) |
| `probes/probe-b-cap.json` | The ten-event cap, `recommendedAIModel`, and the factor-isolating follow-ups Probe A's results demanded | **Round trip run** — see [Recorded results](#recorded-results) |
| `probes/probe-d-pawscript-runtime.json` ([build spec](probe-d-pawscript-runtime.md)) | SoG-without-conditions, `or`/`and` in conditions, chance-formula dialect (`if(…)`, bare `$handle`, `turn_number` forms), same-turn state visibility, pass order, errored one-shots vs `triggerPrereqs`, multi-level / runtime-key record creation | **Round trip + played** — see [Answered by Probe D](#answered-by-probe-d-2026-08-22-played) |
| `probes/probe-e-scope-q10.json` | P10-followup (entry vs item scope level), `recommendedAIModel` bogus-value control, Q10 (absent `triggerConditions` key) | **Two round trips + played** — see [Answered by Probe E](#answered-by-probe-e-2026-08-28-two-round-trips--played) |

All four have been run, and their `-imported.json` counterparts are committed as evidence.
Probe D was driven end-to-end (import, export, play, World Debug) by the Playwright harness in
[`harness/`](harness/README.md); use it for the next round rather than clicking.
The A, B and E source files **now fail validation** — see
[Expected validator output](#expected-validator-output), which explains why that is the
correct end state rather than a regression.

Do not publish any of these worlds.

> **On import risk.** These were originally split so that a hard import failure on the risky
> probes could not take the valuable ones down with it. Probe A's run largely falsified that
> premise: IW's import is **lenient and lossy**, not strict and rejecting. Every unrecognized
> construct in Probe A — two legacy gate shapes, one condition missing `textComparison`, and
> one `"player"`-scoped per-character entry — was silently dropped while the world imported
> successfully. (The array `initialPCValue` was the *pre-probe* suspect and turned out to be
> fine; Probe B's 2×2 cleared it.) Rejection is
> no longer the failure mode to design around; **silent deletion is**. That is why Probe B now
> carries the follow-ups rather than a third file existing to isolate them.

---

## Procedure

1. **Import** the probe JSON into Infinite Worlds via the world edit screen.
2. **Export** the world JSON immediately, before playing and before opening any field in
   the UI editor. Save it alongside the source as e.g. `probe-a-imported.json`.
3. **Diff** the round trip:
   ```
   compare_worlds("<abs path>/probes/probe-a-core.json", "<abs path>/probe-a-imported.json")
   ```
   Everything the platform rewrote — or deleted — is the answer to a round-trip probe.
4. **Play** a handful of turns for the runtime probes, with **World Debug → Trigger Event
   Status** open. Every probe trigger announces itself with a message beginning `PROBE`.
5. **Export again** after ~5 turns for the probes that need a played state.

### Reading the diff without false positives

Probe A established the real noise floor, which is narrower than expected:

- **Empty-field stripping is field-specific.** `descriptionRequest`, `evaluationRequest`,
  `summaryRequest`, `instructionBlocks`, `loreBookEntries` and `NPCs` were dropped when
  empty — but `contentWarnings: ""`, `previewImage: ""`, `previewImageOptions: []` and
  `autoAdvanceVersion: false` all survived. Do not generalize this to "IW strips empties".
- **Key order held — with two exceptions.** Top-level key order and every array's element order
  came back as authored. But the **per-character `skills` map** was reordered in *both* probes:
  `{"Observation": 3, "Patience": 3}` → `{"Patience": 3, "Observation": 3}`. The world-level
  `skills` *array* held its order, so this is specific to the object — consistent with it being
  deserialized into an unordered map server-side. Don't chase it as a finding. Probe E added a
  second: a `triggerConditions` key *injected* by import (the absent-key normalization) sits
  last in its trigger on that export and moves ahead of `canTriggerMoreThanOnce` on the next
  round trip.
- **IW injects a default in at least one place.** Probe B's character had no
  `portraitPromptDetails` key and came back with `portraitPromptDetails: {}`. Probe A's was
  populated and survived intact. So "lenient and lossy" is not only subtractive — diffing a
  round trip will show additions too.
- **`version` held**, because both probes set `autoAdvanceVersion: false`.
- **No ID was renamed.** All probe IDs are alphanumeric, which is what avoids the
  tracked-item rename hazard. Still match entities by `name`, so that a rename would show up
  as a finding rather than shredding the diff.

**A trigger losing its conditions is not diff noise.** `triggerConditions: []` against a
non-empty input is the single most important thing to look for.

---

## Recorded results

From the Probe A round trip. Record the date and app version when you add to this.

### Answered

**P1 — legacy bare-array gate conditions are silently discarded on import.** The worst of
the three possible branches. Both `triggerPrereqs` and `triggerBlockers` in the pre-v2.4
bare-array shape came back as `"triggerConditions": []`, with the trigger's ID, name and
effects fully intact. `P2a`/`P2b` are the controls — same anchor, same condition type, v2.4
object form — and both round-tripped byte-identical, so the bare array is definitively the
cause.

Consequence: importing a pre-v2.4 world under v2.4 converts every gated trigger into a
conditionless — and therefore **dead** — one (P13, below). There is no error and no warning,
in-game or in the export. Worse, **the exported world validated strictly more cleanly than
the input** at the time — `probe-a-core.json` reported 4 errors / 4 warnings,
`probe-a-imported.json` 0 errors / 4 warnings — because the messages had nothing left to fire
on. (Since v0.21.0 the conditionless-trigger warning catches the aftermath: the imported file
now reports 0 errors / 7 warnings.) Migration is not housekeeping; it is the only thing
standing between a legacy world and losing its gates.

**P3 — the `conditions` registry is author-maintained, not platform-derived.** The array
came back byte-identical: still missing the used-but-undeclared event, still holding the
orphan nobody uses. The platform does not regenerate it. Reading 1 confirmed; the plugin's
sync guidance and both warning directions are correct. It also means the ten-event cap is
*not* enforced by regeneration — Probe B has to find where it is enforced.

**P5 — `hidden_boring` survives import unchanged.** The `[PENDING TEST]` marker can be
cleared.

**P2 (partial) — `firedThisTurn: true` survives the round trip.** Not reset on import, so
it is at minimum author-writable. That weakens the "platform-managed runtime state" reading
without killing it: stored-then-overwritten-at-runtime is still possible. Runtime semantics
remain open.

**P9 (partial), P7 (partial)** — all eight style fields, and the nested `formatSchema` with
`enforceFormat: true`, round-tripped exactly. Storage is confirmed; precedence (P9) and
enforcement recursion (P7) are runtime questions still open.

### Confounded in Probe A, resolved by Probe B

**P6 — `textComparison` is effectively mandatory; `not_equal` was never the problem.**
Probe A dropped the whole condition, but its probe omitted `textComparison`, so the cause was
ambiguous. Probe B's 2×2 settled it:

| `inequality` | `textComparison` | Result |
|---|---|---|
| `not_equal` | `"contains"` | survived byte-identical |
| `at_least` | *absent* | **condition deleted** |
| `at_least` | `"contains"` | survived (control ✓) |
| `not_equal` | `""` | **condition deleted** |

`at_least` is fixture-proven and still died purely for lacking the key, so the fatal factor is
`textComparison`, not the inequality. This clears `not_equal`'s `[PENDING TEST]` marker as
confirmed working, and shows the old validator wording ("silently stripped on IW import")
understated the damage — the condition is destroyed, not the key. Both cases are now errors.

**P10 — `"player"` is fatal on a per-character entry; the array form is fine.** The full 2×2:

| Shape | `initialValueBasedOnPC` | Result |
|---|---|---|
| array | `"character"` | survived |
| string | `"player"` | **entry deleted** |
| array | `"player"` | **entry deleted** |
| string | `"character"` | survived |

Clean main effect, no interaction — the array form of `initialPCValue` is **cleared**, which
was the pre-probe suspect. What survived is `"player"` as the fatal factor.

> **⚠ Known confound — this 2×2 does not establish which *level* is fatal.** The probe design
> deliberately held each entry's `initialValueBasedOnPC` **equal to its backing tracked item's**
> ("so only the intended factor varies" — which was right for the shape-vs-scope question and
> wrong for this one). Entry scope across the four cells is `character, player, player,
> character`; item scope is the *identical* `character, player, player, character`. They covary
> perfectly, so nothing separates:
>
> - **(a)** a player-scoped **entry** is deleted — what `validate_world` assumes, or
> - **(b)** a player-scoped **item** drops its per-character entries — arguably the more
>   natural implementation.
>
> All five tracked *items* did survive byte-identical, including the two backing deleted
> entries — but an item record surviving says nothing about whether its *setting* caused the
> entry's deletion. Under (b) the validator has a false negative (item `"player"` + entry
> `"character"`) and a false positive (the reverse). **Neither cell has ever been imported.**
> The rule errors anyway because it is correct in every observed case and both readings agree
> the world is broken. Resolving this is Probe C's job.

### Answered by Probe B

**P11 — the ten-event cap is not enforced at import.** All twelve `conditions` entries and all
twelve triggers survived with conditions intact; nothing was rejected or truncated. Combined
with P3 ruling out registry regeneration, both import-side mechanisms are now excluded, so the
cap is applied at runtime or is purely advisory. **Still needs play data.**

**P12 — `recommendedAIModel: "smilodon"` is accepted and preserved.** Round-tripped
byte-identical: the first known-authorable value for a field the fixture only ever shows as
`null`. Stated precisely, because it is easy to overclaim — survival proves IW *stores* the
string, not that it validates the field or honours it at runtime. No bogus-model control was
run, so we cannot even show IW rejects a nonsense value. **The `DESIGN_BRIEF_v2.md` §9 open
question was the full enum, and it remains open** — this narrows it by one value rather than
closing it. *(Superseded: the bogus-value control ran in Probe E, 2026-08-28 — IW stores any
string verbatim; there is no enforced enum. See
[Answered by Probe E](#answered-by-probe-e-2026-08-28-two-round-trips--played).)*

### Still open — needs another round trip (Probe C)

**P10-followup — ANSWERED by Probe E (2026-08-28), along with the `recommendedAIModel`
bogus-value control it was paired with.** See
[Answered by Probe E](#answered-by-probe-e-2026-08-28-two-round-trips--played).

**P14 — `triggerOnPawScript` malformed-input handling.** Fixture 1.09 (2026-08) introduced
this condition type with one well-formed sample; the plugin registers it and warns on
non-string / blank `data` and on undeclared `$names`, but has no evidence for what the
platform does with a bad expression. Import-side half is round-trip-answerable — see
[Probe C · P14](#p14--triggeronpawscript-malformed-input) below.

**P15 — `$variableName` inside a `triggerOnRandomChance` formula.** Fixture 1.1 (2026-08)
carries `"$number_of_non_human_friends+round(turn_number%random)"`, which proves the `$` form
survives an IW export but not that it *evaluates*: a formula that resolves to NaN/text may
simply never fire, with no error. The dialect is also mixed (`turn_number` and `random` bare,
the tracked item `$`-prefixed). Runtime-only — see
[Probe C · P15](#p15--variablename-in-a-triggeronrandomchance-formula) below.

### Answered in play (2026-08-22)

Two played rounds, three `wait` turns each, World Debug → Trigger Event Status open. Test
worlds `pawscript_capability_test_world_v0.1.json` / `v0.2.json` and the full protocol live
in the `infinite_worlds_stories` repo under `locked-lesbians/spinoff/`. No round trip was
taken for these worlds — trigger *presence* was confirmed by count, condition *survival* was
not — so results about a condition that never fired are stated as behaviour, not mechanism.

**P13 — a trigger with no conditions stays dormant.** Six triggers authored with
`"triggerConditions": []` (two with `canTriggerMoreThanOnce: true`) showed "not yet fired" for
three turns while conditioned triggers in the same world fired normally. Round 2 changed only
one thing — one always-true `triggerOnPawScript` gate (`$probe.n > 0`) on each — and all six
fired on turn 1, the two repeaters every turn. So the P1 aftermath is a **dead** trigger, not
an every-turn one. `validate_world` now warns on any non-SoG trigger with empty/absent
`triggerConditions` (v0.21.0). The `triggerOnStartOfGame: true` + no conditions variant was
closed by Probe D (below): it fires.

**P14a (runtime control) — a well-formed `triggerOnPawScript` survives import and fires.**
`"$probe.n > 2"` against a YAML item fired on turn 1 and, lacking `canTriggerMoreThanOnce`,
fired once; `"$probe.z > 2"` (false) never fired. Firing is only possible with a surviving
condition, so this is the P14a cell. P14b–P14f and the cap question stay open.

**P15a, and the `$`-reference half of P15b — answered.** `"100"` fired every turn (P15a), and
`"choose($probe.n, 3, 100, 0)"` fired, which proves a `$`-handle with a YAML dot path
resolves inside a random-chance formula and drives the roll. P15c, P15d, the bare `"$handle"`
form and the comparison-operator mechanism were all closed by Probe D (next section).

### Answered by Probe D (2026-08-22, played)

Built per [the spec](probe-d-pawscript-runtime.md), imported, exported **immediately**, and
diffed — `compare_worlds` showed all 21 trigger conditions byte-identical, so nothing below is
confounded by import deletion. Then played on Lynx with illustrations off: the opening turn IW
generates at game start (turn 1) plus three `wait` turns. Evidence: the source and
`probe-d-imported.json` here, and the World Debug / tracked-items / Expression Sandbox
transcripts under [`harness/`](harness/README.md#probe-d-evidence-kept-here).

**Step 0 — the round-2 confound is settled: runtime-dead, not deleted.** The imported v0.2
world re-exported with `TstTC04a`, `TstTC05a` and `TstTP03a` conditions unchanged, and World
Debug names the failure for each ("Its condition couldn't be worked out, so the trigger didn't
run"): `Field 'ghost' not found`, `Cannot apply '*' to text and a number`, `Cannot apply '+'
to text values`. The validator's warnings on those shapes stay warnings; the docs now state
the mechanism instead of hedging.

| Q | Cells | Result | Reading |
|---|---|---|---|
| **Q2** SoG with `[]` | #1, #2 | both "fired turn 0"; both `effectShowMessage` popups appeared before the character screen | `triggerOnStartOfGame` is its own gate. The validator's SoG exemption is correct, not a guess. |
| **Q10** absent key | #3 | **not run** — see below | — |
| P13 re-check | #3 (`[]`) | survived import byte-identical; "not yet fired" after four turns | The `[]` shape is runtime-dead, not deleted. |
| **Q3** `or` / `and` | #4, #5, #6 | all fired turn 1 | Boolean operators work in conditions. #5 (missing path on the **right** of `or`) fired while round 2's `TstTP03a` (missing path on the **left**) errored → `or` short-circuits left-to-right. Put the branch that is guaranteed to exist first. |
| **Q4** chance dialect | #7–#12 | `if($probe.n > 2, 100, 0)`, bare `$probe.hundred`, `$probe.n + 97`, `$game.turn_number * 100` and bare `turn_number * 100` all fired turn 1; bare `$probe.z` (0) never fired | Every numeric form works and the value drives the roll. Both `turn_number` spellings resolve. The only dead shape is a comparison used as a number (Step 0). |
| **Q5** same-turn write → later condition | #13, #14 | #14 "fired turn 1", the turn #13 set `flag` | Conditions evaluate against live, intra-pass state, not start-of-turn state. |
| **Q6** pass order | #15, #16, #20, #21 | `order_keys` = `"amanda"` on turn 1, `"amanda,late,deep,dyn"` on turn 2, while the panel already showed all four on turn 1 | List order confirmed: the earlier consumer ran before the later producers within the pass. |
| **Q7** errored one-shot | #17, #18, #19 | #17 logged "A script stopped early, on line 1 — Field 'ghost' not found", `err_ran` stayed PENDING, yet the trigger list shows it "fired turn 1"; #18 (prereq on #17) and #19 (control) both fired | Rollback is not a retry **and** the consumed trigger still satisfies `triggerPrereqs` downstream. |
| **Q8** creation depth / runtime key | #20, #21 | both fired; the Subjects panel shows `deep: {stats: {trust: 1}}` and `dyn: {suspicion: 1}` | Multi-level creation and `.item($k)` creation both work. |

**Q10 was not run.** While bisecting an editor failure during the build, the absent-key
trigger was swapped for `[]` and the real cause turned out to be unrelated — the tracked
items lacked `description` (see
[`PLATFORM_BEHAVIOR_NOTES.md`](../references/mechanics/PLATFORM_BEHAVIOR_NOTES.md#other-import-findings);
the trigger's name in the JSON still carries the wrong attribution). The absent-key cell was
answered by Probe E (2026-08-28), below: normalized to `[]` at import, equally dead.

**Expression Sandbox (zero-credit) findings, round-2 world at turn 2** — transcript in
`harness/probe-d-sandbox-results.txt`:

- A condition must come out `true`/`false`. A number (`if(…)`, `choose(…)`, `$x + 97`,
  `$game.turn_number`, a bare `$handle`, `random`) gets "not true or false — so the trigger
  never fires". So P14e (non-boolean expression) is answered: dormant, never misfires.
- `$nosuch > 0` → `No tracked item or variable called 'nosuch'`; a missing YAML path →
  `Field 'x' not found`; `.item("ghost").suspicion` → "add a fallback: `.item("ghost", fallback)`".
  So P14d (undeclared `$name`) is answered at runtime: the condition errors and never fires.
- `==` is rejected: "PawScript compares with a single '=' — write `$hp = 10`, not `$hp == 10`".
- `not`, `and`, `or` all evaluate; `.exists()` is safely false on a missing record.
- `$game.turn_number` and bare `turn_number` both resolve (to the same number).
- `random` (bare) is a 0–1 float; `random(1,100)` also returned 0–1 values in two samples, so
  do not assume the argument form scales the range.
- An empty expression errors ("Empty expression - nothing to evaluate").

### Answered by Probe E (2026-08-28, two round trips + played)

Built by [`harness/build_probe_e.py`](harness/build_probe_e.py), driven end-to-end by the
harness: import → export (`probe-e-imported.json`) → re-import of that export → export again
(`probe-e-imported-2.json`) → new game, the opening turn plus two `wait` turns with World Debug open
(`harness/probe-e-turn*-debug.txt`).

**P10-followup — the ENTRY's own scope value drives the delete, and entry scope is a
projection of the item's.** The two covariance-breaking cells:

| Cell | Item scope | Entry scope (authored) | Round trip 1 | Round trip 2 |
|---|---|---|---|---|
| PE1 | `"player"` | `"character"` | entry KEPT, but exported with scope rewritten to `"player"` | entry DELETED |
| PE2 | `"character"` | `"player"` | entry DELETED | fresh entry auto-created from the item (`""` value, scope `"character"`) |

So the old reading (a) is confirmed for the delete decision — import deletes any incoming
entry whose own `initialValueBasedOnPC` is `"player"`, whatever the item says — but the
deeper model is that entry-level scope is not an independent field at all: IW stores/exports
it as a copy of the item's, and a `"character"`-scoped item that *arrives with no entry*
gets one auto-created on import (a deleted entry is not re-created in the same import —
round trip 1's export has no PE2 entry). Consequences: (1) the validator's entry-level error
stands, now unhedged; (2) NEW warning — an entry backed by a `"player"`-scoped item survives
one import but the next export/import round trip silently deletes it (PE1's fate), so the
state is non-round-trippable (whether IW's own editor can even construct it is untested —
P4 remains open); (3) **IW's export is not always re-importable byte-stable** — PE1 is the
first observed case of an IW export that IW's own import then mutates (see the invariant
caveat under [Expected validator output](#expected-validator-output)).

**P12-followup — `recommendedAIModel` has no import-time validation.** `"notarealmodel"`
survived both round trips verbatim: IW applies no enum check to unknown strings in this
field, so the `DESIGN_BRIEF_v2.md` §9 "full enum" question is closed for import-time
validation — there is no enforced enum to discover. Stated precisely, as P12 itself was:
this is survival, not semantics. Untested: whether known-*retired* names are stripped from
this field (AI_RUNTIME_MECHANICS.md confirms that only for `selectedAIProfiles`), and
whether the runtime honors the value. The plugin correctly type-checks string-or-null and
goes no further.

**Q10 — an absent `triggerConditions` key is normalized to `[]` at import and is
runtime-dead.** The exported trigger carries `"triggerConditions": []`; in play it sat at
"not yet fired" for three turns while the always-true `triggerOnPawScript` control fired
every turn (fired 3 times). The absent-key case now has the same confirmed status as `[]`:
dead, not unconditional. `_check_conditionless_triggers`' warning covers both shapes with
no remaining hedge.

### Still open — all runtime-only

P2 semantics (does `firedThisTurn: true` narrow the gate?), P4's editor-UI read, P7
enforcement recursion, P8 YAML coercion, P9 image precedence, P11 firing behaviour, and the
cap half of P14 (does a `triggerOnPawScript` gate count toward the ten-event cap?). None of
these can be read from a round trip; each needs a played session or a generated image.

---

## Probe A

### P0 — Anchor
`P0 Anchor` fires on turn 1 and is the referent for every gate probe. If it does not fire,
nothing downstream is interpretable.

### P1 — legacy gate conditions *(round trip answered — see above)*
The runtime half — does a trigger left with `triggerConditions: []` fire every turn, or
never? — was answered in play on 2026-08-22 (P13, above): **never**. The deleted gate leaves a
dead trigger, and the fix wording follows from that.

### P2 — What is `firedThisTurn`? *(round trip partially answered)*
`P2a` sets `true`, `P2b` is the `false` control, both gate on the anchor. The anchor fires
on turn 1 only, so from turn 2 the anchor has fired *at some point* but not *this turn*. If
`P2a` goes quiet from turn 2 while `P2b` keeps firing, `firedThisTurn: true` narrows the
gate to the current turn. Also check whether the trigger editor exposes a checkbox for it —
if it does not, that still favours the platform-managed reading despite the value surviving.

### P3 — the `conditions` registry *(answered — author-maintained)*
One runtime question is left: the `P3a` trigger's event is declared nowhere. If it still
fires when its event occurs in the narrative, undeclared events evaluate at runtime and are
merely invisible to the editor's dropdown.

### P4 — How is the registry's text matched?
`conditions` holds `Probe P4 Near  Miss Event Marker.` (title case, double space, trailing
period); the trigger holds `PROBE P4 NEAR MISS EVENT MARKER`. Both survived the round trip
separately, which tells us nothing — the platform does not touch `conditions` at all, so
this can only be read **in the editor UI**: is the trigger shown bound to the declared entry,
or to nothing?

### P5 — `hidden_boring` *(answered — survives)*

### P6 — `not_equal` *(confounded — see Probe B P6a–P6d)*

### P7 — Does `enforceFormat` recurse into nested sub-maps?
Storage is confirmed. The runtime read: the item's update instructions deliberately tell the
AI to **omit** the nested `stats` block on each entry it adds. Play several turns, then read
the value in World Debug.

- Entries keep gaining a well-formed `stats` sub-map → enforcement recurses.
- Entries appear with `name`/`breed` but no `stats` → enforcement stops at the top level, and
  a nested script path is **not** made safe by `enforceFormat`.

`P7 Nested YAML script walk` runs `$entry.stats.friendliness += 1` from turn 2. Scripts are
transactional, so a single drifted entry rolls the whole run back — watch for the increment
failing across *all* entries, which is itself the confirmation that non-recursive enforcement
is a real hazard.

### P8 — Does IW's YAML parser coerce `yes`/`no`/`on`/`off`?
The JSON string round-trips trivially; this is runtime-only. Read the rendered value in
World Debug. Coercion to `true`/`false` means YAML 1.1 and the defensive-quoting advice in
[`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md) is
load-bearing. Literal words mean YAML 1.2 and the advice can soften to a note.

### P9 — Which image-style fields win?
All three marker sets survived import, so the question is entirely visual:

| Field set | Marker |
|---|---|
| `illustrationStyle*HighPriority` | stark black-and-white charcoal sketch |
| `illustrationStyle*LowPriority` | muted sepia daguerreotype |
| `imageStyle*Pre` / `*Post` (legacy) | vivid neon cyberpunk photograph |

Generate a character portrait **and** a scene image, then judge which marker the output
matches. **Confound:** `imageStyle` is separately set to the `photo_1` preset. If the output
matches none of the three, the preset is dominating — re-run with a different preset.

### P10 — array `initialPCValue` *(confounded — see Probe B P10a–P10d)*

---

## Probe B

### P11 — What does the ten-event cap actually do?

Twelve declared events, twelve triggers, one `triggerOnEvent` each. Events 11 and 12 name
themselves as past the cap.

| Outcome | Conclusion |
|---|---|
| Import rejected | Hard cap enforced at import. |
| Export returns 10 entries | Silent truncation — record *which* ten survive. |
| All 12 survive, all 12 fire | The cap is advisory/cost guidance, not a limit. |
| All 12 survive, only 10 ever fire | Runtime cap. Record which two are dead. |

P3 ruled out the "platform regenerates `conditions`" explanation for how the cap is enforced,
so whatever happens here is the actual mechanism. The answer also settles whether the cap
counts `conditions` entries or distinct `triggerOnEvent` strings — the validator currently
takes the max of both.

### P12 — Is `recommendedAIModel: "smilodon"` valid?

Survives the round trip → one confirmed enum value, and the field is authorable. Reset to
`null` → `"smilodon"` is not accepted there (it may be `selectedAIProfiles`-only). Given
Probe A's lenient-lossy behaviour, a silent reset is now the likeliest outcome and an import
rejection the least. Cross-check against the model dropdown in the world editor.

### P6a–P6d — why did Probe A's `triggerOnTrackedItem` condition get dropped?

Four variants against one shared target item holding `3`. All four conditions are **true**,
so every one of them should fire if it survived import.

| Probe | `inequality` | `textComparison` | Tests |
|---|---|---|---|
| P6a | `not_equal` | `"contains"` | `not_equal` alone |
| P6b | `at_least` | *absent* | absent key alone |
| P6c | `at_least` | `"contains"` | positive control, mirrors the fixture |
| P6d | `not_equal` | `""` | the empty-string case |

Read `triggerConditions` in the export, then confirm against which `PROBE P6…` messages
appear in play:

| Observed | Conclusion |
|---|---|
| P6c survives, P6b dropped | **A missing `textComparison` is fatal**, and `not_equal` was never the problem. |
| P6c and P6b survive, P6a dropped | **`not_equal` is rejected** — the `[PENDING TEST]` marker becomes a confirmed failure. |
| Both P6a and P6b dropped | Both factors are independently fatal. |
| P6c dropped too | Something about this probe's construction is wrong, not the platform — discard the run. |

P6d is separate: the validator claims an empty-string `textComparison` is "silently stripped
on IW import". If P6d comes back with the key gone but the condition intact, that claim is
right. If the whole condition is gone, the warning understates the damage and should say so.

### P10a–P10d — why did Probe A's menu entry get dropped?

The full 2×2 across `initialPCValue` shape and `initialValueBasedOnPC` value. Item-level and
entry-level `initialValueBasedOnPC` are kept consistent in every cell so only the intended
factor varies.

| Probe | `initialPCValue` | `initialValueBasedOnPC` | Note |
|---|---|---|---|
| P10a | array | `"character"` | The combination the canonical fixture demonstrates |
| P10b | string | `"player"` | Isolates `"player"` |
| P10c | array | `"player"` | Replicates Probe A's dropped cell |
| P10d | string | `"character"` | Baseline — Probe A showed this survives |

| Observed | Conclusion |
|---|---|
| P10a survives, P10c dropped | The **pairing** is invalid — arrays require `"character"`. |
| P10a and P10c both dropped | The **array form itself** is fragile here; the fixture's use of it may depend on something this probe does not reproduce. |
| P10b dropped | `"player"` is the problem on its own, independent of shape. |
| All four survive | Probe A's drop had a cause neither factor explains — re-examine that world. |

### P13 — does a trigger with no conditions fire, or stay dormant? *(answered in play 2026-08-22 — dormant)*

`P13 Empty triggerConditions` is authored with `"triggerConditions": []` — exactly the state
Probe A showed a legacy gate gets reduced to. This was the missing half of P1: if it fired
every turn, importing a legacy world would turn its gated triggers into **unconditional
every-turn triggers**. It does not — the in-platform play rounds recorded above showed the
empty-array case never fires, so a stripped gate leaves a dead trigger. The SoG variant
(`triggerOnStartOfGame: true` with no conditions) remains open.

---

## Expected validator output

**The Probe A, B and E source files fail validation, and that is correct.** Do not "fix" them.

An earlier version of this file said that a validator change making these probes error "means
the change needs rethinking". That guard was written when the probes were instruments waiting
to be run, and it no longer applies: both have been run, their results are recorded above, and
the plugin has since been taught that the constructs they carry are destructive. The files are
now **historical records of things that break**, so the validator agreeing with them is the
intended end state.

`probes/probe-a-core.json` — 4 errors, 4 warnings. The errors are P1a and P1b (legacy
bare-array gates), P6 (missing `textComparison`) and P10 (`"player"`-scoped entry) — the four
constructs the probes proved IW deletes. The warnings are the `conditions`-registry desyncs,
which are genuinely warnings: P3 showed a desync costs editor selectability, not correctness.

`probes/probe-b-cap.json` — 4 errors, 2 warnings. Errors: P6b, P6d, P10b, P10c. Warnings: the
twelve-events-over-ten cap (P11), which stays a warning because import-time enforcement was
ruled out and runtime enforcement is untested; and the P13 trigger's empty `triggerConditions`
(v0.21.0 — a conditionless trigger never fires).

`probes/probe-d-pawscript-runtime.json` — 0 errors, 1 warning (the `[]` trigger), and
`probe-d-imported.json` reports exactly the same because nothing was deleted.

`probes/probe-e-scope-q10.json` — 1 error, 2 warnings. Error: PE2's player-scoped entry
(deleted on import, as predicted). Warnings: the Q10 conditionless trigger, and PE1's entry
backed by a player-scoped item (the v0.22.0 doomed-entry warning).

The useful invariant is the inverse one, and it *almost* holds: **every `-imported.json` file
validates with zero errors**, because IW already deleted everything the validator now objects
to — with one instructive exception. `probe-e-imported.json` reports **1 error**: IW's own
export of the PE1 cell carries the entry rewritten to `"player"` scope, a state IW's own next
import deletes (`probe-e-imported-2.json` — 0 errors, 1 warning — proves it). So the
exception confirms the validator rather than contradicting it: the error names data that
really is one round trip away from vanishing. Everywhere else the validator's errors and the
platform's deletions line up exactly. (The imported files do carry warnings —
`probe-a-imported.json` 7, `probe-b-imported.json` 4 — because every condition IW deleted
left behind a conditionless, dead trigger, which the v0.21.0 warning now names.)

The three canonical fixtures must continue to validate with **zero errors** (`CLAUDE.md`
source-of-truth rule 1). That is why the legacy-gate rule is version-conditional rather than
flat — see [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md).

---

## Probe C *(designed, not yet built)*

Carries P14 (the P10-followup cells it originally also carried were run as Probe E,
2026-08-28, and the P15 write-up below is retained as historical record — its cells are
closed). Build it as `probes/probe-c-pawscript.json` when there is a round trip to spend;
keep it minimal like the others.

### P14 — `triggerOnPawScript` malformed input

The v2.4 fixture (world version 1.09) is itself an IW export, so a well-formed
`triggerOnPawScript` — `data: "$favorite_flavor = \"Lemon\""` — is already known to survive a
round trip. What is unknown is the failure mode, and Probe A's lesson is that IW's failure
mode is *silent deletion*, not rejection. Six triggers, one condition each, one shared text
tracked item `probe_flavor` holding `"Lemon"`, each trigger's `effectShowMessage` naming
its own cell:

| Cell | `data` | Import-side question |
|---|---|---|
| P14a (control) | `"$probe_flavor = \"Lemon\""` | Survives byte-identical (expected — the fixture proves it). |
| P14b | `""` | Blank string: kept, or deleted like an empty `textComparison`? |
| P14c | *(key absent)* | Missing `data`: kept, or deleted? |
| P14d | `"$no_such_item = 1"` | Undeclared `$name`: kept verbatim (author error is a runtime concern), or rejected/deleted at import? |
| P14e | `"$probe_flavor"` | Non-boolean expression (a bare string value): kept? |
| P14f | `"<<probe_flavor>> = \"Lemon\""` | Legacy `<<…>>` interpolation inside a condition: kept, rewritten, or deleted? |

Import outcomes drive the validator: a deleted P14b/P14c promotes the current warning to a
version-conditional error (same shape as the legacy-gate rule); a deleted P14d promotes the
undeclared-`$name` warning likewise; a *kept* P14f means the plugin should warn that
`<<…>>` is the wrong form rather than stay silent.

**Runtime half (played session):** P14a is answered — a well-formed condition survives import
and fires (2026-08-22, see "Answered in play"). P14d/P14e are answered at runtime by the
Expression Sandbox (see "Answered by Probe D"): an undeclared `$name` errors and a
non-boolean result "never fires" — dormant, never a misfire. The import-side cells (is the
condition *kept*?) are still Probe C's. Still open: with ten
`triggerOnEvent` conditions already declared, does adding a `triggerOnPawScript` gate push
the world past the cap — i.e. does the platform count it as an AI-evaluated event? The
plugin presumes not (`_MAX_AI_EVENT_CONDITIONS` counts `triggerOnEvent` only); a contrary
result changes that count.

### P15 — `$variableName` in a `triggerOnRandomChance` formula

The v2.4 fixture (world version 1.1) exports `"$number_of_non_human_friends+round(turn_number%random)"`
as a random-chance formula, so the `$` form is at least author-writable and export-stable.
Everything else is a played-session question. One number tracked item `probe_odds`, four
triggers with `canTriggerMoreThanOnce: true`, each `effectShowMessage` naming its cell:

| Cell | `data` | `probe_odds` | Runtime question |
|---|---|---|---|
| P15a (control) | `"100"` | — | **Answered 2026-08-22:** fires every turn. |
| P15b | `"$probe_odds"` | `100` | **Answered 2026-08-22 (Probe D #8):** the bare `"$handle"` form fires. |
| P15c | `"$probe_odds"` | `0` | **Answered (Probe D #9):** never fires across four turns — the value drives the roll. |
| P15d | `"$game.turn_number*100"` | — | **Answered (Probe D #11/#12):** fires from turn 1, and so does bare `"turn_number*100"` — both spellings resolve. |

All four cells are closed; the docs drop the "bare `turn_number` only" caveat and keep the
fixture's additive idiom (Probe D #10 fired). Optional import-side cell: a
`"$no_such_item"` formula, to learn whether an undeclared `$name` is deleted on import the way
P14d asks for `triggerOnPawScript`.

---

## After the run

Six findings from these two round trips landed in v0.18.0: P1, P3, P5, P6, P10 and P12. Three
validator rules changed with them — the legacy-gate warning became a version-conditional
error, the `textComparison` warning became an error and gained a missing-key case, and
`"player"`-scoped per-character entries became an error.

For future runs, findings land in three places, in this order:

1. **`references/world_v2.4.schema.json`** — rewrite the relevant `x-iw-note`. These notes
   are the single source of truth; `SCHEMA_SUMMARY` derives from them at import time.
2. **The reference docs** — [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md),
   [`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md),
   [`references/fields/IMAGE_STYLE.md`](../references/fields/IMAGE_STYLE.md), and
   [`references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`](../references/mechanics/PLATFORM_BEHAVIOR_NOTES.md)
   for import/export behaviour rather than field definitions.
3. **`src/iw_architect/validator.py`** — a warning may become an error once its behaviour is
   confirmed harmful, or be dropped once confirmed harmless. Add a negative test either way.

Record the date and the app version alongside each answer. These are empirical results
against a moving platform, not schema facts.
