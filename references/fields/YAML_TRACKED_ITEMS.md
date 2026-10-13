# Field Guide: YAML Tracked Items

JSON key: `trackedItems[*]` — the same array covered by
[`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md). This file covers the **structured**
tracked-item format introduced in schema v2.2: `dataType: "yaml"` and its
companion fields `variableName`, `formatSchema`, `formatExample`, and
`enforceFormat`. Read [`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md) first for the
general when-to-track / `visibility` / `updateInstructions` judgment; this file
is only about the YAML shape and the PawScript handle.

For exact field shapes see
[`WORLD_JSON_SCHEMA_v2.4.md`](../WORLD_JSON_SCHEMA_v2.4.md#4-trackeditems) §4.

---

## YAML is the recommended structured format

v2.2 makes **YAML the preferred way to store structured tracked-item state.**
When a tracked item needs to hold more than a single scalar — a list of records,
a map of stats, a small database — reach for `dataType: "yaml"`. It reads
cleanly, the AI produces it reliably, and it's the format PawScript's collection
functions (`.count()`, `.where(…)`, `for each`, …) are designed to walk. See
[`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md).

### The four `dataType` values

| `dataType` | Use for | Notes |
|---|---|---|
| `text` | Inventory lists, location names, qualitative states, comma-separated tags | Most flexible scalar. Supports the `contains` / `does_not_contain` comparisons in `triggerOnTrackedItem` (`does_not_contain` editor-observed 2026-09-30, import unprobed). |
| `number` | Health, gold, counters, skill scores, meters | Required for arithmetic and the `at_least` / `is_exactly` / `at_most` / `not_equal` operators. |
| `yaml` | **Structured state** — lists of records, maps of stats, mini-databases | **Recommended** structured format. Walkable by PawScript collection functions. |
| `xml` | Legacy structured state | **DEPRECATED.** Older worlds used `xml` for structured state. Preserve it on round-trip, but author new structured items as `yaml`. |

If you're deciding between `text` and `yaml`: use `text` for a flat scalar or a
simple comma-separated list; use `yaml` the moment each entry has multiple
fields, or you want to iterate/filter entries from PawScript.

---

## The whole YAML language is supported — including nesting

**A `dataType: "yaml"` item can hold any valid YAML structure, to any depth.** There
is no flat-key restriction and no "one level of records" limit. If it is legal YAML,
it is a legal tracked-item value.

Flat examples can read as a flat ceiling; there isn't one. The authoritative author-facing
reference is **<https://infiniteworlds.app/yaml-guide>**, and everything it teaches is
usable here:

| Shape | Example | Guide step |
|---|---|---|
| Labels and scalars | `gold: 120` | 1–2 |
| Lists | `- apples`<br>`- pears` | 3 |
| Lists of records | `- name: Spot`<br>`  breed: mixed` | 4 |
| **Nesting** — a map inside a map | `sword:`<br>`  damage: 8`<br>`  weight: 5` | 5 |
| **Lists inside things** — and records inside those lists, recursively | `skills:`<br>`  - id: fireball`<br>`    depends_on:`<br>`      - flame_dart` | 6 |
| Empty list | `depends_on: []` | 6 |
| Block scalars — `\|` keeps your line breaks, `>` folds into one line | `backstory: \|`<br>`  She lost her family.`<br>`  Now she studies fire magic.` | 7 |
| Comments | `# ignored by the parser` | 8 |
| Quoting to protect literal text | `answer: "yes"` | 9 |

Mix them freely. A record in a list can contain a map, which can contain another
list of records, as deep as the data actually goes:

```yaml
- name: Spot
  breed: mixed
  stats:
    friendliness: 5
    energy: 10
  tricks:
    - name: sit
      reliability: 0.9
    - name: rollover
      reliability: 0.4
  color: spotted black and white
```

**Depth is a cost decision, not a capability question.** The AI has to reproduce the
whole shape every turn it updates the item, so each level of nesting is one more thing
that can drift. Nest because the data is genuinely hierarchical — grouping a record's
stats under `stats:` is meaningful — not to show off. A three-level structure the AI
maintains reliably beats a six-level one it mangles.

Two things follow the nesting automatically:

- **`formatSchema` mirrors it** — see the next section.
- **PawScript walks it with dots** — `$puppy.stats.friendliness`, `$puppy.tricks.count()`.
  See [`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md).

---

## The structured-format fields

Four fields work together to define and enforce a YAML item's shape.

| Field | Type | What it does |
|---|---|---|
| `variableName` | string (snake_case, **unique**) | The item's PawScript handle — `$<variableName>`. See below. |
| `formatExample` | string | An **example value** in the item's format — shows the AI (and you) what a well-formed value looks like. |
| `formatSchema` | string | A **pseudo-schema** describing the item's structure, line by line. |
| `enforceFormat` | boolean | When `true`, the platform **enforces** `formatSchema` on the item's value. When `false`, `formatSchema` is advisory only. |

### `variableName` — the PawScript symbol

`variableName` is the snake_case, **unique** handle used to address the
item from PawScript as `$<variableName>` (e.g. `variableName: "player_gold"` →
`$player_gold`). Keep it:

- **snake_case** — lowercase words joined by underscores.
- **unique** across the world — it's a symbol; collisions are ambiguous.
- **derived from the item's name** — and it is *not* stable across a rename (see
  below), so treat a rename as a handle change.

**Renaming an item regenerates its handle** — *owner-observed, not
probe-verified:* renaming a tracked item in the Edit World editor re-derives
`variableName` from the new Name. Every `$old_handle` in an `effectRunScript`, a
`triggerOnPawScript` gate or a `triggerOnRandomChance` formula then points at
nothing unless it is updated too. After a rename, grep the world for the old
handle; `validate_world` warns on a `$name` in those three places that is no
longer any item's `variableName`.

**It is JSON-only.** The Edit World screen does not show `variableName` at all
(observed by the repo owner, and absent from the 2026-09-30 screen survey), so an
author can set or change it only in the world JSON.

**How IW derives it from `name`** — *owner-observed, not probe-verified:* IW
generates the handle from the tracked item's Name by lowercasing it and replacing
whitespace and special characters with underscores. An item named
`Elena's Private Read` gets `elena_s_private_read`, addressed in PawScript as
`$elena_s_private_read`. The six tracked items in the canonical fixture fit
that rule only if each *run* of whitespace and special characters becomes a
single underscore: `Number of Non-Human Friends` → `number_of_non_human_friends`
is consistent either way, but `Puppy Tracking - YAML Format Tracked Items` →
`puppy_tracking_yaml_format_tracked_items` has one `_` where a character-by-character
replacement of ` - ` would give three. The fixture can't show whether those handles
were generated or typed, so it doesn't settle what IW does with runs.

**An authored value is kept on import, not re-derived.** Probe C imported an item
named `PC Flavor` with `variableName: "probe_flavor"`, and the export came back
with `probe_flavor` unchanged (`probes/probe-c-pawscript.json` vs
`probes/probe-c-imported.json`, 2026-08-29), and `$probe_flavor` resolved at runtime (Probe C P14a fired every turn). Probe E's `PE1 Item-Player Entry-Character` → `pe1_item_player` likewise survived two round trips. So when you write a world by hand,
the handle you write is the handle scripts must use, even if it differs from what
the name would derive.

**Plugin convention when authoring a handle:** lowercase the name, turn each run of
whitespace and special characters into **one** `_`, and drop any leading or trailing
`_`. That reproduces all six fixture handles and the owner's example, and it always
satisfies the validator's `^[a-z][a-z0-9_]*$` check, except when the name starts
with a digit or has non-ASCII letters (see below), or has no ASCII letters or digits
at all (which leaves an empty handle). Then adjust the handle by hand. It is the plugin's choice, not a verified copy of IW's algorithm.

**Still unverified** (don't rely on any of these until probed):

- **Absent `variableName`.** Does import generate a handle for an item that has
  none? Every fixture and probe tracked item carries one, so this has never been
  observed. Always author it.
- **Runs of special characters.** Does IW turn `A - B` into `a_b` or `a___b`? The
  fixture's `Puppy Tracking - YAML …` → `puppy_tracking_yaml_…` is the one
  data point, and it points to collapsing, but the fixture can't show whether IW
  generated it.
- **Leading and trailing underscores.** Does a name ending in `?` or `'` leave a
  trailing `_`, or one starting with `'` a leading `_`? The validator warns on a
  leading `_`.
- **Digits, and a leading digit in particular.** `validate_world` warns on any
  handle that doesn't match `^[a-z][a-z0-9_]*$`, so a generated `2nd_wind` would
  be flagged. Whether IW ever generates one is unknown.
- **Non-ASCII letters** (`Café`, `Ñandú`): transliterated, kept, or replaced? A
  kept non-ASCII letter would fail the validator's `^[a-z][a-z0-9_]*$` check (a
  warning).
- **Collisions.** Two items whose names derive the same handle: does IW suffix
  one, or emit a duplicate? `validate_world` warns on duplicates either way.
- **What a rename touches.** A rename regenerates the handle (above), but does IW
  also rewrite scripts and expressions that use the old one, and does it overwrite
  a handle that was hand-authored in the JSON? The platform-managed
  `driftAcknowledgedForName` field (only ever `null` in the fixture) may relate
  to this, but that is a guess.

### `formatSchema` syntax

`formatSchema` is a lightweight pseudo-schema, one field per line:

- `field: text` or `field: number` — declares a field and its type.
- `field:` with **nothing after the colon and no children** — declares a field
  with **no type constraint** (any scalar). This is how the canonical fixture declares
  its boolean field: `has_scent:` in the schema, `has_scent: true` / `false` in the
  example. `text` and `number` are the only named types the fixture uses; there is
  no `boolean` keyword, so leave the type blank for booleans (and for anything else
  you'd rather not pin down).
- `field:` with **indented children** — declares a field whose value is a sub-map.
- `...:` — a **continuation marker** meaning "more entries like the ones above"
  (i.e., the structure repeats — it's a list of these records, not a fixed set).
  It can appear at **any level**, not just the outermost one.

**The pseudo-schema mirrors the value's own nesting.** It is not restricted to a
flat list of leaf fields. This is the fixture's puppy tracker:

```
- name: text
  breed: text
  stats:
    friendliness: number
    energy: number
    ...:
  color: text
  has_scent: 
  ...:
```

Read it top-down: a **list of records**; each record has `name`, `breed`, a `stats`
sub-map, `color`, and an untyped `has_scent`. Inside `stats`, `friendliness` and
`energy` are numbers, and the nested `...:` says more stat keys are allowed there.
The trailing outer `...:` says the list may hold any number of such records.

Compare to the matching `formatExample`, which is the same shape filled in:

```yaml
- name: Spot
  breed: mixed
  stats:
    friendliness: 5
    energy: 10
  color: spotted black and white
  has_scent: true
```

### `formatExample` vs. `formatSchema` vs. `enforceFormat`

- `formatSchema` is the **shape**; `formatExample` is a **filled-in sample** of
  that shape. Provide both — the schema tells the AI the rules, the example
  shows the rules satisfied.
- `enforceFormat: true` turns `formatSchema` from a suggestion into a
  constraint the platform holds the value to. Use it when downstream PawScript
  depends on the fields being present and correctly typed (e.g., a script that
  does `$puppy.stats.friendliness += 1` needs `stats.friendliness` to exist and
  be a number). Use `enforceFormat: false` (or omit) for advisory structure where
  the AI has more latitude.
- **Whether enforcement recurses into sub-maps is unverified.** The fixture proves
  the platform *stores* a nested `formatSchema`; nothing proves it *enforces* one,
  or that enforcement descends past the top level. Treat a nested `formatSchema`
  as strong guidance to the AI rather than a hard guarantee — and don't rely on it
  to make a nested script **read** path unconditionally safe. This matters because
  scripts are transactional: one drifted entry rolls back the entire run. Pure
  writes are the easier case — a plain assignment to a missing path creates it
  (confirmed 2026-08-22, one level under an existing map), so `enforceFormat` earns
  its keep on items a script *reads* structurally (`+=`, `for each` over a
  sub-field), not on items it merely writes to. See
  [`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md#5-statement-set-scripts-only) §5.

---

## YAML quoting gotchas

YAML's implicit typing bites structured tracked items in two common ways. Both
turn a value you meant as *text* into something else:

- **Leading-zero strings become numbers.** Unquoted `007` parses as the number
  `7` — the zeros are lost. Quote it: `"007"`.
- **`true` / `false` become booleans.** Unquoted `true` is the boolean `true`,
  not the string `"true"`. Quote it when you mean the literal word: `"true"`.
  When you *want* a boolean — the fixture's `has_scent: true` — leave it unquoted
  and declare the field untyped (`has_scent:`) in `formatSchema`.
  (Some YAML parsers also coerce `yes` / `no` / `on` / `off` to booleans; whether
  IW's parser does is unverified — quote those too when you mean literal text, to
  be safe.)

**Rule of thumb:** any value that is *meant to be literal text* — codes,
IDs, on/off words, anything with leading zeros — should be **quoted**. When in
doubt, quote.

---

## Worked example — the puppy tracker

A real fixture item (`sVHX9pTft`) that stores a list of puppy records and bumps
their friendliness each turn via a script. **It is deliberately nested** — each
record's numeric stats live under a `stats:` sub-map — so that the canonical
example demonstrates depth rather than implying a flat ceiling.

**Tracked item:**

- `dataType: "yaml"`
- `variableName: "puppy_tracking_yaml_format_tracked_items"`
- `enforceFormat: true`
- `formatSchema`:

  ```
  - name: text
    breed: text
    stats:
      friendliness: number
      energy: number
      ...:
    color: text
    has_scent: 
    ...:
  ```

- `formatExample` / `initialValue`:

  ```yaml
  - name: Spot
    breed: mixed
    stats:
      friendliness: 5
      energy: 10
    color: spotted black and white
    has_scent: true
  ```

**The `effectRunScript` that walks it** (a "Run a script" trigger effect):

```
for each $puppy in $puppy_tracking_yaml_format_tracked_items
  $puppy.stats.friendliness += 1
```

Note the path: `$puppy.stats.friendliness`, not `$puppy.friendliness`. **Chaining
dots is all nesting costs at the script layer** — a field two levels down is no
harder to reach than a top-level one, which is why grouping related fields into a
sub-map is essentially free once the AI is reliably producing the shape.

`enforceFormat` is `true` here, which is the strongest available signal that every
entry will carry a `stats` map with a numeric `friendliness` — though whether the
platform enforces *through* the nesting is unverified (see above), so treat it as
very likely rather than guaranteed. The loop
variable `$puppy` is assignable and writes back to the real item — see
[`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md#5-statement-set-scripts-only)
§5. The whole script is transactional: if any entry were malformed, nothing
would change and the error would land in World Debug.

## Worked example — a map of records

A list is not the only walkable shape. A **map of records** — keyed by name, one
sub-map per key — is the shape that supports creating a record on the fly, and
`for each` / `.keys()` walk it too (confirmed in play 2026-08-22).

**Tracked item** (`variableName: "subjects"`, `dataType: "yaml"`,
`enforceFormat: true`):

- `formatSchema`:

  ```
  amanda:
    suspicion: number
  ...:
    suspicion: number
  ```

- `initialValue`:

  ```yaml
  amanda:
    suspicion: 1
  ```

**A script that adds a record, then walks the map:**

```
$subjects.newgirl.suspicion = 7
set $c = 0
for each $w in $subjects
  set $c = $c + 1
$results.s6_count = $c
$results.s6_keys = $subjects.keys().join(",")
```

With the value `amanda:\n  suspicion: 1\nnewgirl:\n  suspicion: 7`, `for each`
counted 2 and `.keys().join(",")` gave `amanda,newgirl`. The first line created
`newgirl` under the existing map (see `PAWSCRIPT.md` §5, "Writes create; reads
don't"); the record conformed to the `...:` continuation in `formatSchema` and
survived subsequent turns. Reading a key that does not exist
(`$subjects.ghost.suspicion`) is the case that rolls the script back — guard it
with `$subjects.ghost.exists()`.

---

## Cross-references

- **The YAML language itself** — <https://infiniteworlds.app/yaml-guide> is the
  author-facing guide, and IW supports all of it: labels, lists, nesting, lists
  inside things, block scalars (`|` and `>`), comments, and quoting. Point authors
  there rather than re-teaching YAML.
- **PawScript** — [`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md) for how
  `$<variableName>` items are read and mutated, and the collection functions
  that walk YAML lists/maps.
- **Tracked items (general)** — [`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md) for
  `visibility`, the per-turn processing cost, and `updateInstructions`.
- **Trigger effects** — [`TRIGGER_EVENTS.md`](./TRIGGER_EVENTS.md) for
  `effectRunScript` and the other effects that read/write tracked items.
- **Schema shapes** — [`WORLD_JSON_SCHEMA_v2.4.md`](../WORLD_JSON_SCHEMA_v2.4.md#4-trackeditems) §4.
