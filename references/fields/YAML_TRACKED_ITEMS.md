# Field Guide: YAML Tracked Items

JSON key: `trackedItems[*]` — the same array covered by
[`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md). This file covers the **structured**
tracked-item format introduced in schema v2.2: `dataType: "yaml"` and its
companion fields `variableName`, `formatSchema`, `formatExample`, and
`enforceFormat`. Read [`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md) first for the
general when-to-track / `visibility` / `updateInstructions` judgment; this file
is only about the YAML shape and the PawScript handle.

For exact field shapes see
[`WORLD_JSON_SCHEMA_v2.2.md`](../WORLD_JSON_SCHEMA_v2.2.md#4-trackeditems) §4.

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
| `text` | Inventory lists, location names, qualitative states, comma-separated tags | Most flexible scalar. Supports `contains` comparison in `triggerOnTrackedItem`. |
| `number` | Health, gold, counters, skill scores, meters | Required for arithmetic and the `at_least` / `is_exactly` / `at_most` operators. |
| `yaml` | **Structured state** — lists of records, maps of stats, mini-databases | **Recommended** structured format. Walkable by PawScript collection functions. |
| `xml` | Legacy structured state | **DEPRECATED.** Older worlds used `xml` for structured state. Preserve it on round-trip, but author new structured items as `yaml`. |

If you're deciding between `text` and `yaml`: use `text` for a flat scalar or a
simple comma-separated list; use `yaml` the moment each entry has multiple
fields, or you want to iterate/filter entries from PawScript.

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

`variableName` is the stable, snake_case, **unique** handle used to address the
item from PawScript as `$<variableName>` (e.g. `variableName: "player_gold"` →
`$player_gold`). Keep it:

- **snake_case** — lowercase words joined by underscores.
- **unique** across the world — it's a symbol; collisions are ambiguous.
- **derived from the item's name** but stable — renaming the display `name`
  shouldn't force a `variableName` change, because scripts reference the handle,
  not the display name.

### `formatSchema` syntax

`formatSchema` is a lightweight pseudo-schema, one field per line:

- `field: text` or `field: number` — declares a field and its type.
- `...:` — a **continuation marker** meaning "more entries like the ones above"
  (i.e., the structure repeats — it's a list of these records, not a fixed set).

```
- name: text
  breed: text
  friendliness: number
  energy: number
  color: text
  ...:
```

That schema describes a **list of records**, each with the five named fields;
the trailing `...:` says the list may hold any number of such records.

### `formatExample` vs. `formatSchema` vs. `enforceFormat`

- `formatSchema` is the **shape**; `formatExample` is a **filled-in sample** of
  that shape. Provide both — the schema tells the AI the rules, the example
  shows the rules satisfied.
- `enforceFormat: true` turns `formatSchema` from a suggestion into a
  constraint the platform holds the value to. Use it when downstream PawScript
  depends on the fields being present and correctly typed (e.g., a script that
  does `$puppy.friendliness += 1` needs `friendliness` to exist and be a
  number). Use `enforceFormat: false` (or omit) for advisory structure where
  the AI has more latitude.

---

## YAML quoting gotchas

YAML's implicit typing bites structured tracked items in two common ways. Both
turn a value you meant as *text* into something else:

- **Leading-zero strings become numbers.** Unquoted `007` parses as the number
  `7` — the zeros are lost. Quote it: `"007"`.
- **`true` / `false` become booleans.** Unquoted `true` is the boolean `true`,
  not the string `"true"`. Quote it when you mean the literal word: `"true"`.
  (Some YAML parsers also coerce `yes` / `no` / `on` / `off` to booleans; whether
  IW's parser does is unverified — quote those too when you mean literal text, to
  be safe.)

**Rule of thumb:** any value that is *meant to be literal text* — codes,
IDs, on/off words, anything with leading zeros — should be **quoted**. When in
doubt, quote.

---

## Worked example — the puppy tracker

A real fixture item that stores a list of puppy records and bumps their
friendliness each turn via a script.

**Tracked item:**

- `dataType: "yaml"`
- `variableName: "puppy_tracking_yaml_format_tracked_items"`
- `enforceFormat: true`
- `formatSchema`:

  ```
  - name: text
    breed: text
    friendliness: number
    energy: number
    color: text
    ...:
  ```

**The `effectRunScript` that walks it** (a "Run a script" trigger effect):

```
for each $puppy in $puppy_tracking_yaml_format_tracked_items
  $puppy.friendliness += 1
```

Because `enforceFormat` is `true`, every entry is guaranteed to carry a numeric
`friendliness` field, so the script's `+= 1` is safe. The loop variable
`$puppy` is assignable and writes back to the real item — see
[`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md#5-statement-set-scripts-only)
§5. The whole script is transactional: if any entry were malformed, nothing
would change and the error would land in World Debug.

---

## Cross-references

- **PawScript** — [`mechanics/PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md) for how
  `$<variableName>` items are read and mutated, and the collection functions
  that walk YAML lists/maps.
- **Tracked items (general)** — [`TRACKED_ITEMS.md`](./TRACKED_ITEMS.md) for
  `visibility`, the per-turn processing cost, and `updateInstructions`.
- **Trigger effects** — [`TRIGGER_EVENTS.md`](./TRIGGER_EVENTS.md) for
  `effectRunScript` and the other effects that read/write tracked items.
- **Schema shapes** — [`WORLD_JSON_SCHEMA_v2.2.md`](../WORLD_JSON_SCHEMA_v2.2.md#4-trackeditems) §4.
