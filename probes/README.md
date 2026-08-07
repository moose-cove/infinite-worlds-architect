# Schema probes

Instrument worlds for the schema v2.4 questions the plugin currently answers with
"unverified". Each probe is a deliberately minimal world whose only job is to make the
platform reveal a behaviour we cannot read out of the schema, the canonical fixture, or
the wiki.

| File | Covers | Status |
|---|---|---|
| `probes/probe-a-core.json` | Gate-condition shapes, `firedThisTurn`, the `conditions` registry, `hidden_boring`, `not_equal`, nested YAML, image-style precedence, menu-backed `initialPCValue` | **Round trip run** — see [Recorded results](#recorded-results) |
| `probes/probe-b-cap.json` | The ten-event cap, `recommendedAIModel`, and the factor-isolating follow-ups Probe A's results demanded | Not yet run |

Both validate clean (`valid: true`). Every warning `validate_world` emits on them is an
intended probe, not a defect — see [Expected validator warnings](#expected-validator-warnings).

Do not publish either world.

> **On import risk.** These were originally split so that a hard import failure on the risky
> probes could not take the valuable ones down with it. Probe A's run largely falsified that
> premise: IW's import is **lenient and lossy**, not strict and rejecting. Every unrecognized
> construct in Probe A — two legacy gate shapes, one malformed condition, one array
> `initialPCValue` — was silently dropped while the world imported successfully. Rejection is
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
- **Key order held.** Both probes are authored in IW's canonical order and came back in it.
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
exported world validates with fewer warnings than the input**, because the legacy-shape
warning has nothing left to fire on. Migration is not housekeeping; it is the only thing
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

### Confounded — reruns folded into Probe B

**P6** — the whole `triggerOnTrackedItem` condition was dropped, same as P1. But the probe
omitted `textComparison`, so the result cannot distinguish "IW rejects `not_equal`" from
"IW rejects a condition with no `textComparison`". Probe B's P6a–P6d isolate the two factors.

**P10** — the array `initialPCValue` + `"player"` entry was dropped entirely while the
string + `"character"` control survived. But with no array + `"character"` control in the
probe, the array form, the `"player"` value, and the pairing are all still live suspects.
Probe B's P10a–P10d complete the 2×2.

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

## Expected validator warnings

All intentional; do not "fix" them.

**`probes/probe-a-core.json`** (6) — two pre-v2.4 bare-array gate warnings (P1a, P1b), two
undeclared-`triggerOnEvent` warnings (P3a, P4), two orphan-declared-event warnings (P3C and
P4's near-miss entry).

**`probes/probe-b-cap.json`** (2) — one empty-string `textComparison` warning (P6d, which is
the probe), and one twelve-events-over-the-cap-of-ten warning (P11).

If a future validator change makes these files error rather than warn, the probes have become
unimportable and the change needs rethinking.

---

## After the run

Findings land in three places, in this order:

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
