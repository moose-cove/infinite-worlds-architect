# Schema probes

Instrument worlds for the schema v2.4 questions the plugin currently answers with
"unverified". Each probe is a deliberately minimal world whose only job is to make the
platform reveal a behaviour we cannot read out of the schema, the canonical fixture, or
the wiki.

| File | Covers | Status |
|---|---|---|
| `probes/probe-a-core.json` | Gate-condition shapes, `firedThisTurn`, the `conditions` registry, `hidden_boring`, `not_equal`, nested YAML, image-style precedence, menu-backed `initialPCValue` | **Round trip run** — see [Recorded results](#recorded-results) |
| `probes/probe-b-cap.json` | The ten-event cap, `recommendedAIModel`, and the factor-isolating follow-ups Probe A's results demanded | **Round trip run** — see [Recorded results](#recorded-results) |

Both have now been run, and their `-imported.json` counterparts are committed as evidence.
Both source files **now fail validation** — see
[Expected validator output](#expected-validator-output), which explains why that is the
correct end state rather than a regression.

Do not publish either world.

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
- **Key order held — with one exception.** Top-level key order and every array's element order
  came back as authored. But the **per-character `skills` map** was reordered in *both* probes:
  `{"Observation": 3, "Patience": 3}` → `{"Patience": 3, "Observation": 3}`. The world-level
  `skills` *array* held its order, so this is specific to the object — consistent with it being
  deserialized into an unordered map server-side. Don't chase it as a finding.
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

Consequence: importing a pre-v2.4 world under v2.4 converts every gated trigger into an
ungated one. There is no error and no warning, in-game or in the export. Worse, **the
exported world validates strictly more cleanly than the input** — `probe-a-core.json` reports
4 errors / 4 warnings, `probe-a-imported.json` 0 errors / 4 warnings — because the messages
have nothing left to fire on. Migration is not housekeeping; it is the only thing standing
between a legacy world and losing its gates.

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
closing it.

### Still open — needs another round trip (Probe C)

**P10-followup — which level is fatal, the entry or its backing item?** The only unresolved
question that a round trip *can* answer, and the one carrying a live validator rule. Probe C
needs exactly two cells, both of which break the entry/item covariance every existing cell has:

| Tracked item `initialValueBasedOnPC` | Entry `initialValueBasedOnPC` | Distinguishes |
|---|---|---|
| `"player"` | `"character"` | survives ⇒ reading (a); entry deleted ⇒ reading (b) |
| `"character"` | `"player"` | entry deleted ⇒ reading (a); survives ⇒ reading (b) |

If reading (b) wins, `_check_initial_tracked_item_value_scope` must key off the tracked item
rather than the entry, and `test_check_reads_the_entry_not_the_item_in_an_untested_platform_cell`
is the assertion that has to flip. Worth pairing with a `recommendedAIModel` bogus-value
control (does IW reject an unknown model string, or store anything?) since both are cheap.

**P14 — `triggerOnPawScript` malformed-input handling.** Fixture 1.09 (2026-08) introduced
this condition type with one well-formed sample; the plugin registers it and warns on
non-string / blank `data` and on undeclared `$names`, but has no evidence for what the
platform does with a bad expression. Import-side half is round-trip-answerable — see
[Probe C · P14](#p14--triggeronpawscript-malformed-input) below.

### Still open — all runtime-only

P2 semantics (does `firedThisTurn: true` narrow the gate?), P4's editor-UI read, P7
enforcement recursion, P8 YAML coercion, P9 image precedence, P11 firing behaviour, P13
(does a condition-less trigger fire every turn or stay dormant?), and the runtime half of P14
(does a `triggerOnPawScript` gate count toward the ten-event cap, and is a non-boolean
expression treated as false?). None of these can be read from a round trip; each needs a
played session or a generated image.

---

## Probe A

### P0 — Anchor
`P0 Anchor` fires on turn 1 and is the referent for every gate probe. If it does not fire,
nothing downstream is interpretable.

### P1 — legacy gate conditions *(round trip answered — see above)*
The remaining question is runtime: does a trigger left with `triggerConditions: []` fire
every turn, or never? Both are wrong, but it changes how the fix should be worded. Probe B's
P13 answers it directly.

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

### P13 — does a trigger with no conditions fire, or stay dormant?

`P13 Empty triggerConditions` is authored with `"triggerConditions": []` — exactly the state
Probe A showed a legacy gate gets reduced to. This is the missing half of P1: if it fires
every turn, then importing a legacy world turns its gated triggers into **unconditional
every-turn triggers**, which is materially worse than them going dormant, and the validator
wording should reflect that.

---

## Expected validator output

**Both probe source files now fail validation, and that is correct.** Do not "fix" them.

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

`probes/probe-b-cap.json` — 4 errors, 1 warning. Errors: P6b, P6d, P10b, P10c. Warning: the
twelve-events-over-ten cap (P11), which stays a warning because import-time enforcement was
ruled out and runtime enforcement is untested.

The useful invariant is the inverse one, and it holds: **both `-imported.json` files validate
with zero errors**, because IW already deleted everything the validator now objects to. The
validator's errors and the platform's deletions line up exactly. If that ever stops being
true, something has drifted.

The three canonical fixtures must continue to validate with **zero errors** (`CLAUDE.md`
source-of-truth rule 1). That is why the legacy-gate rule is version-conditional rather than
flat — see [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md).

---

## Probe C *(designed, not yet built)*

Carries the P10-followup cells above plus P14. Build it as `probes/probe-c-pawscript.json`
when there is a round trip to spend; keep it minimal like the others.

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

**Runtime half (played session):** with all surviving cells present, does P14a fire and do
P14d/P14e stay dormant (expression treated as false) or misfire? And with ten
`triggerOnEvent` conditions already declared, does adding a `triggerOnPawScript` gate push
the world past the cap — i.e. does the platform count it as an AI-evaluated event? The
plugin presumes not (`_MAX_AI_EVENT_CONDITIONS` counts `triggerOnEvent` only); a contrary
result changes that count.

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
