# Schema probes

Instrument worlds for the schema v2.4 questions the plugin currently answers with
"unverified". Each probe is a deliberately minimal world whose only job is to make the
platform reveal a behaviour we cannot read out of the schema, the canonical fixture, or
the wiki.

| File | Covers | Import risk |
|---|---|---|
| `probes/probe-a-core.json` | Gate-condition shapes, `firedThisTurn`, the `conditions` registry, `hidden_boring`, `not_equal`, nested YAML, image-style precedence, menu-backed `initialPCValue` | Low |
| `probes/probe-b-cap.json` | The ten-event cap, `recommendedAIModel` enum | Higher — isolated on purpose |

They are split so that a hard import failure on the risky probes costs nothing on the
valuable ones. **Run Probe A first.** Do not publish either world.

Both validate clean today (`valid: true`). Every warning `validate_world` emits on them is
an intended probe, not a defect — see [Expected validator warnings](#expected-validator-warnings).

---

## Procedure

1. **Import** the probe JSON into Infinite Worlds via the world edit screen.
   - If import fails outright, that is itself a finding. Record the error text and stop.
2. **Export** the world JSON immediately, before playing and before opening any field in
   the UI editor. Save it as e.g. `probe-a-imported.json`.
3. **Diff** the round trip:
   ```
   compare_worlds("<abs path>/probes/probe-a-core.json", "<abs path>/probe-a-imported.json")
   ```
   Everything the platform rewrote on import is the answer to a round-trip probe.
4. **Play** a handful of turns for the runtime probes (P1, P2, P3, P4, P6, P7, P8), with
   **World Debug → Trigger Event Status** open. Every probe trigger announces itself with a
   message beginning `PROBE`.
5. **Export again** after ~5 turns for the probes that need a played state.

### Reading the diff without false positives

Three platform behaviours produce diff noise that means nothing:

- **Field reordering.** IW renormalizes to its canonical key order on import. Both probes
  are already authored in that order (see
  [`references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`](../references/mechanics/PLATFORM_BEHAVIOR_NOTES.md)),
  so reordering should be minimal — but ignore it where it appears.
- **`version` drift.** Both probes set `autoAdvanceVersion: false` to hold `version` still.
  If it moves anyway, that is a (minor) finding about `autoAdvanceVersion`, not about a probe.
- **Stripped false booleans.** IW strips optional booleans set to their default. An absent
  `autoAdvanceVersion` in the export is expected, not a probe result.

**Match entities by `name`, never by `id`.** All probe IDs are alphanumeric specifically to
dodge the silent tracked-item ID-rename hazard, so IDs *should* survive — but if any ID does
change, that is a finding to record, and name-matching keeps the rest of the diff readable.

---

## Probe A

### P0 — Anchor
`P0 Anchor` fires on turn 1 and is the referent for every gate probe. If it does not fire,
nothing downstream is interpretable. Confirm it first.

### P1 — Does the platform migrate the legacy bare-array gate condition?

**The highest-consequence unknown in v2.4.** Two triggers carry the pre-v2.4 shape
(`"data": ["PrbAnchr"]`) instead of the v2.4 object shape.

*Round-trip read:* look at `P1a` / `P1b` `triggerConditions[0].data` in the export.

| Export shows | Conclusion |
|---|---|
| `{"prereqs": [...], "firedThisTurn": ...}` | Platform migrates on import. Legacy worlds are safe untouched. |
| `["PrbAnchr"]` unchanged | No migration. Behaviour then depends on the runtime read below. |
| `data` gone / emptied | Platform discards the unrecognized shape — **legacy gates silently stop gating**. |

*Runtime read* (use `P2b` as the control — it is the same gate in v2.4 object form):

| Observed from turn 2 | Conclusion |
|---|---|
| `P1a` fires and `P1b` stays silent, matching `P2b` | Legacy shape honoured. |
| `P1a` silent while `P2b` fires | Legacy prereqs evaluate as unmet — gate over-blocks. |
| `P1b` fires despite the anchor having fired | Legacy blockers ignored — **gate over-fires, the dangerous case**. |

`P1a` firing on turn **1** (before the anchor) would mean the unparsed condition is treated
as vacuously true.

### P2 — What is `firedThisTurn`?

`P2a` sets `firedThisTurn: true`; `P2b` is the `false` control. Both gate on the anchor.

*Round-trip read:* if the export resets `P2a` to `false`, `firedThisTurn` is
platform-managed runtime state, not an authoring knob. If `true` survives, it is authorable.

*Runtime read:* the anchor fires on turn 1 only. So from turn 2 onward the anchor has fired
*at some point* but not *this turn*. If `P2a` goes quiet from turn 2 while `P2b` keeps firing,
`firedThisTurn: true` narrows the gate to the current turn — the hypothesis the reference
docs currently call plausible-but-unverified.

*UI read:* check whether the trigger editor exposes a checkbox for it at all. If it does not,
that is strong evidence for the platform-managed reading.

### P3 — Is the `conditions` registry author-maintained or platform-derived?

The world declares three events and uses three, deliberately mismatched:

- `PROBE P3A unregistered event marker` — **used** by a trigger, **not declared**
- `PROBE P3B registered event marker` — used and declared (control)
- `PROBE P3C orphan declared event marker` — **declared**, used by nothing

*Round-trip read:*

| Export's `conditions` | Conclusion |
|---|---|
| Gained P3A and/or dropped P3C | **Platform-derived.** The plugin should stop treating it as author-owned. |
| Unchanged (still missing P3A, still holding P3C) | **Author-maintained.** Current guidance is correct. |

*Runtime read:* if the P3a trigger fires when its event occurs in the narrative despite never
being declared, an undeclared event still evaluates at runtime — which settles the
"undeclared events are invisible to the dropdown but live at runtime" half of reading 1.

### P4 — How is the registry's text matched?

`conditions` holds `Probe P4 Near  Miss Event Marker.` (title case, a double space, a
trailing period). The trigger's `triggerOnEvent` holds `PROBE P4 NEAR MISS EVENT MARKER`
(all caps, single spaces, no period).

If the platform links them anyway — the export collapses them, or the editor shows the
trigger bound to the declared entry — matching is normalized, and the plugin's exact-match
warning is too strict. If they stay separate, exact matching is confirmed.

### P5 — Does `hidden_boring` survive import?

One tracked item is authored `"visibility": "hidden_boring"`. Read it back in the export.
Survives → the KB's `[PENDING TEST]` marker can be cleared. Coerced to `hidden` or
`ai_only` → the plugin should say so.

### P6 — Does `not_equal` survive import?

`P6 not_equal inequality` compares a tracked item holding `3` against a required value of
`99`, so `not_equal` is true and the trigger should fire from turn 1.

Round-trip: check `inequality` is still `not_equal` in the export. Runtime: if the message
never appears despite the value being 3, the condition did not survive intact.

### P7 — Does `enforceFormat` recurse into nested sub-maps?

`P7 Nested Yaml Enforce` has `enforceFormat: true` and a `formatSchema` nesting a `stats`
sub-map. Its update instructions deliberately tell the AI to **omit** `stats` on each new
entry it adds — an instruction that conflicts with the schema, on purpose.

Play several turns, then read the item's value in World Debug:

- Entries keep gaining a well-formed `stats` sub-map → enforcement recurses.
- Entries appear with `name`/`breed` but no `stats` → enforcement stops at the top level,
  and a nested script path is **not** made safe by `enforceFormat`.

The `P7 Nested YAML script walk` trigger runs `$entry.stats.friendliness += 1` on turn 2+.
Scripts are transactional, so if any entry has drifted the whole run rolls back — watch for
the increment silently failing across *all* entries, which is itself the confirmation that
non-recursive enforcement is a real hazard.

### P8 — Does IW's YAML parser coerce `yes`/`no`/`on`/`off`?

`P8 Yaml Scalar Coercion` holds unquoted `yes`, `no`, `on`, `off`, `true`, `007`, `1.10`,
plus a quoted `"yes"` control. Read the rendered value in World Debug.

`yes`/`no`/`on`/`off` rendering as `true`/`false` means a YAML 1.1 parser and the
defensive-quoting advice in
[`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md)
is load-bearing. Rendering as the literal words means YAML 1.2, and the advice can be
softened to a note.

### P9 — Which image-style fields win?

Every style field is populated with a mutually exclusive, visually unmistakable marker:

| Field set | Marker |
|---|---|
| `illustrationStyle*HighPriority` | stark black-and-white charcoal sketch |
| `illustrationStyle*LowPriority` | muted sepia daguerreotype |
| `imageStyle*Pre` / `*Post` (legacy) | vivid neon cyberpunk photograph |

Generate a character portrait **and** a scene image, then judge which marker the output
looks like. That is the precedence order, for that slot.

**Confound to watch:** `imageStyle` is separately set to the `photo_1` preset. If the output
matches none of the three markers, the preset is dominating — re-run with a different preset
before drawing conclusions.

### P10 — Does an array `initialPCValue` work with `initialValueBasedOnPC: "player"`?

The probe character's entry for `P10 Menu Item Probe` pairs a three-option array with
`"player"` — the combination the canonical fixture never demonstrates.

At character selection, either the three `PROBE P10 OPTION …` values are offered as a
pick-one menu (combination works), or they are not (the array form requires `"character"`,
and the plugin should say so).

---

## Probe B

Run only after Probe A is recorded, and expect this one to be the more likely to fail.

### P11 — What does the ten-event cap actually do?

Twelve declared events, twelve triggers, one `triggerOnEvent` each. Events 11 and 12 name
themselves as past the cap.

| Outcome | Conclusion |
|---|---|
| Import rejected | Hard cap enforced at import. |
| Export returns 10 entries | Silent truncation — record *which* ten survive (first ten? last ten?). |
| All 12 survive, all 12 fire | The cap is advisory/cost guidance, not a limit. |
| All 12 survive, only 10 ever fire | Runtime cap. Record which two are dead. |

Whatever the answer, it also settles whether the cap counts `conditions` entries or distinct
`triggerOnEvent` strings — the validator currently takes the max of both.

### P12 — Is `recommendedAIModel: "smilodon"` valid?

Survives the round trip → one confirmed enum value, and the field is authorable.
Reset to `null` → `"smilodon"` is not accepted there (it may be `selectedAIProfiles`-only).
Import fails → the field validates against a closed enum; read the error for the allowed set.

Cross-check against the model dropdown in the world editor, which should name the full set.

---

## Expected validator warnings

`validate_world` reports these on the probe files. All are intentional; do not "fix" them.

**`probes/probe-a-core.json`** — two pre-v2.4 bare-array gate warnings (P1a, P1b), two
undeclared-`triggerOnEvent` warnings (P3a, P4), two orphan-declared-event warnings (P3C,
P4's near-miss entry).

**`probes/probe-b-cap.json`** — one twelve-events-over-the-cap-of-ten warning (P11).

If a future validator change makes these files error rather than warn, the probes have
become unimportable and the change needs rethinking.

---

## After the run

Findings land in three places, in this order:

1. **`references/world_v2.4.schema.json`** — rewrite the relevant `x-iw-note`. These notes
   are the single source of truth; `SCHEMA_SUMMARY` derives from them at import time.
2. **The reference docs** — [`references/fields/TRIGGER_EVENTS.md`](../references/fields/TRIGGER_EVENTS.md),
   [`references/fields/YAML_TRACKED_ITEMS.md`](../references/fields/YAML_TRACKED_ITEMS.md),
   [`references/fields/IMAGE_STYLE.md`](../references/fields/IMAGE_STYLE.md), and
   [`references/mechanics/PLATFORM_BEHAVIOR_NOTES.md`](../references/mechanics/PLATFORM_BEHAVIOR_NOTES.md)
   for anything that is import/export behaviour rather than a field definition.
3. **`src/iw_architect/validator.py`** — a warning may become an error once its behaviour is
   confirmed harmful, or be dropped once confirmed harmless. Add a negative test either way.

Record the date and the app version alongside each answer. These are empirical results
against a moving platform, not schema facts.
