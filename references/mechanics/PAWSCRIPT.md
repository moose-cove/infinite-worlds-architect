# PawScript

PawScript is Infinite Worlds' small expression-and-scripting language. It comes
in two flavors that look similar but are governed by different rules:

- **Expressions** — read-only lookups written inside `<<…>>` brackets, legal
  anywhere adventure text is typed. `<<health>>`, `<<puppies.count()>>`.
- **Scripts** — imperative blocks that live *only* inside the "Run a script"
  trigger effect (`effectRunScript`) and can *only* mutate tracked items. No
  `<< >>` brackets.

This document tells you what each flavor can do, where each is legal, the
variable and function vocabulary they share, and the statement set scripts add
on top. Read it before writing any `<<…>>` interpolation more complex than a
bare tracked-item name, or before authoring an `effectRunScript` effect.

> **Documentation status.** PawScript is a live platform feature and its
> surface evolves. This document describes expected behavior as of schema
> v2.4, cross-checked against the official PawScript guides (linked in §7). If
> observed behavior contradicts what's documented here, flag the discrepancy to
> the user rather than silently working around it — surfacing drift is how the
> docs stay correct.

---

## 1. Expressions vs. scripts — the distinction that matters

Everything downstream follows from this table. Get it wrong and you'll try to
mutate a tracked item from a narrative field (impossible) or show a message
from a script (impossible).

| | **Expressions** `<<…>>` | **Scripts** |
|---|---|---|
| Where they live | Anywhere adventure text is typed: narrative `instructions`, tracked-item `initialValue` / `description`, trigger conditions, AI prompt fields | **Only** inside the `effectRunScript` trigger effect |
| Brackets | Wrapped in `<< >>` | No brackets — the whole effect body is the script |
| Can read state | Yes | Yes |
| Can change state | **No — read-only** | **Yes — but only tracked items** |
| Can show messages / talk to the AI / write native fields | No | **No** |
| On error | Harmless — renders nothing | Transactional rollback — nothing changes, logged to World Debug |
| Loops / branches | No — a single expression | Yes — `for each`, `if` / `else if` / `else` |

**The "if the editor lets you type it" rule of thumb.** If the IW editor lets
you type `<<health>>` in a given text box today, you can write *any* expression
there. Expressions are legal in every field that accepts adventure text.

**Scripts are narrow on purpose.** A script's only job is to compute new
tracked-item values. It cannot show the player a message (that's
`effectShowMessage`), cannot instruct the AI (that's `effectTellAIWhatToDo`),
and cannot touch native platform fields. If you need any of those, use the
dedicated trigger effect — not a script.

---

## 2. Variables

PawScript exposes three kinds of variable. Two are read-only natives; the third
is your tracked items.

| Symbol | What it is | Access |
|---|---|---|
| `$player` | The active player character | **Read-only.** e.g. `$player.name` |
| `$game` | Current game/session state | **Read-only.** e.g. `$game.turn_number` |
| `$<variableName>` | A tracked item, by its `variableName` | Read anywhere; **assignable in scripts only** |

- **Natives (`$player`, `$game`) are always read-only**, in both expressions
  and scripts. You cannot assign to `$player.name` or `$game.turn_number`.
- **Tracked items are addressed by their `variableName`** — the snake_case,
  unique handle set on each tracked item (see
  [`fields/YAML_TRACKED_ITEMS.md`](../fields/YAML_TRACKED_ITEMS.md)). A tracked
  item whose `variableName` is `player_gold` is `$player_gold` in PawScript.
- Inside a script, `$<variableName>` is an **assignment target**:
  `$player_gold += 10` writes the new value back (transactionally).

> **Expressions and the legacy `<<…>>` syntax.** In narrative text you still
> reference tracked items and skills the classic way — `<<health>>`,
> `<<skill_charm>>`, `<<turn_number>>` — the interpolation vocabulary in
> [`WORLD_JSON_SCHEMA_v2.4.md`](../WORLD_JSON_SCHEMA_v2.4.md#9-template-variable-system)
> §9. The `$`-prefixed native form is the PawScript-native way to reach the
> same state; see §6 for how the two coexist.

---

## 3. Expressions (`<<…>>`)

Expressions are **read-only lookups**. They compute a value and render it in
place. They never change state.

**Where they're legal.** Anywhere adventure text is typed:

- Narrative and AI-facing fields — `instructions`, `authorStyle`,
  `descriptionRequest`, EIB/KIB content, and so on.
- Tracked-item `initialValue` and `description`.
- Trigger conditions (the platform evaluates the expression to decide whether
  the condition holds). The dedicated condition type is **`triggerOnPawScript`**
  — see below. A `triggerOnRandomChance` formula can also read a tracked item as
  `$variableName` — see below.
- AI prompt fields.

**`triggerOnPawScript` — an expression as a trigger gate.** Fixture 1.09
(2026-08) added a condition type whose `data` is a bare PawScript boolean
expression, written in the `$variableName` form with *no* `<<…>>` brackets:

```jsonc
{
  "category": "condition",
  "type": "triggerOnPawScript",
  "data": "$favorite_flavor = \"Lemon\"",
  "id": "e95ded8d-1a55-d946-f9a9-22b65f99886d"
}
```

The platform evaluates it each turn against live tracked-item values and fires
the trigger when it is truthy. It is deterministic — no AI judgment, so it is
presumed not to count toward the ten-event `triggerOnEvent` cap (unverified).
Compound tests go inside the one expression (`$gold >= 50 and $puppies.count > 2`)
rather than across several conditions under a `logic` node, and it can reach into
YAML sub-fields with the same dot paths scripts use (§5). Every `$name` in it must
be a tracked item's `variableName` or a native; `validate_world` warns on anything
else, and on a `data` that is not a non-empty string. A malformed or non-boolean
expression survives import unchanged and simply **never fires** (Probe D + Expression
Sandbox, 2026-08-22): a numeric result is reported as "not true or false — so the
trigger never fires", an unknown `$name` as `No tracked item or variable called 'x'`,
and a missing YAML path as `Field 'x' not found`, with World Debug logging "Its
condition couldn't be worked out, so the trigger didn't run". `and` / `or` / `not` all
work; **`or` short-circuits left-to-right**, so a branch that may not exist goes on the
right (`$probe.n > 2 or $subjects.ghost.suspicion > 0` fires; the reverse errors) or
behind `.exists()`. Equality is a single `=` — `==` is a syntax error. See
[`probes/README.md`](../../probes/README.md). Authoring guidance:
[`TRIGGER_EVENTS.md`](../fields/TRIGGER_EVENTS.md#choosing-condition-types).

**Play-confirmed 2026-08-22.** `"$probe.n > 2"` fired on the turn it became true
and `"$probe.z > 2"` never fired, against a `dataType: "yaml"` item — so numeric
comparison, YAML dot-path reads and true/false gating all work, and the one-shot
default is honoured (the true condition fired once and stayed fired without
`canTriggerMoreThanOnce`). This is the reliable deterministic gate; prefer it over
synthesizing a boolean inside a `triggerOnRandomChance` formula, which was
observed not to fire (see below and `TRIGGER_EVENTS.md`).

**`triggerOnRandomChance` — tracked items inside the chance formula.** Fixture
1.1 (2026-08) shows the random-chance formula reading a tracked item in the same
`$variableName` form:

```jsonc
{
  "category": "condition",
  "type": "triggerOnRandomChance",
  "data": "$number_of_non_human_friends+round(turn_number%random)"
}
```

The chance scales with state — more non-human friends, higher odds — without a
separate `triggerOnPawScript` gate and roll. The dialect is mixed: the fixture
writes `turn_number` and `random` **bare** while the tracked item carries the `$`.
Both spellings of the turn counter resolve here — bare `turn_number` and
`$game.turn_number` each fired a `* 100` formula from turn 1 (Probe D, 2026-08-22) —
so the bare form is a convention, not a requirement. `random` is a 0–1 float (the
Expression Sandbox returned 0.29 / 0.42 for it, and the same range for
`random(1,100)`, so do not assume the argument form rescales it). `validate_world`
warns on a non-string/blank formula and on a `$name` that is not a tracked item's
`variableName` or a native.

At runtime (play-confirmed 2026-08-22, rounds 1–2 and Probe D) the field is a
**numeric** expression and every numeric form tried fires when the value beats the
roll: a literal `"100"`, a bare `"$probe.hundred"` holding 100 (while `"$probe.z"`
holding 0 never fires, so the value really drives the roll), the fixture's additive
idiom (`"$probe.n + 97"`), `"choose($probe.n, 3, 100, 0)"`,
`"if($probe.n > 2, 100, 0)"`, and both `turn_number * 100` spellings. What does
**not** work is a comparison used as a number: `"($x > 2) * 100"` fails with
`Cannot apply '*' to text and a number` and `"((($a > 1) + ($b > 1)) > 0) * 100"`
with `Cannot apply '+' to text values` — a comparison yields **text**, not 0/1, so
the formula errors, World Debug reports "Its condition couldn't be worked out, so
the trigger didn't run", and the trigger never fires. The condition survives import
byte-identical (re-export diffed), so this is a runtime-dead shape, not a deletion.
For conditional odds use `if(cond, a, b)` or `choose(…)`, which return numbers; for
anything that is really a gate, use `triggerOnPawScript`.

**Errors are harmless.** If an expression references something that doesn't
exist or is otherwise malformed, it simply renders nothing — it does not crash
the turn or the game. This makes expressions safe to sprinkle into narrative
text without defensive guards.

**Legacy bare-word expressions remain valid.** The older interpolation
forms — `<<player_name>>`, `<<health>>`, `<<skill_charm>>` — are still fully
supported. You do not need to rewrite existing worlds to a `$`-prefixed style.
New authoring can use either; both resolve against the same underlying state.

```
Your dog is <<puppy_tracking_yaml_format_tracked_items.count()>> strong and growing.
You have <<player_gold>> gold left.
```

---

## 4. Scripts

Scripts run inside the **`effectRunScript`** trigger effect and nowhere else.
Their sole power is to **mutate tracked items**.

**Transactional execution.** A script runs as an all-or-nothing transaction:

- If the script completes without error, all its tracked-item writes are
  applied together.
- If *any* statement errors, **nothing changes** — the platform rolls the whole
  script back, logs the problem to **World Debug**, and the game continues
  normally. A broken script never breaks a turn; it just does nothing and
  leaves a debug breadcrumb.
  **Rollback is not a retry.** The trigger still counts as fired. On a one-shot
  trigger (`canTriggerMoreThanOnce` absent/`false`) an errored script is a
  permanent loss — the trigger is consumed on the turn it fires and never runs
  again, so the writes never land (confirmed 2026-08-22). The consumed trigger
  still counts as fired for `triggerPrereqs` downstream (Probe D: a prereq on the
  errored trigger fired the same turn), so a chain can advance past a step whose
  state change never happened. For any script that
  could touch a path that might not exist, either guard every read with
  `.exists()` or set `canTriggerMoreThanOnce: true` so a later turn can succeed.

**Bounded loops only.** Scripts cannot loop unboundedly. You may only iterate
over a finite collection — a list, a map, or `range(n)`. There is no
`while`-style construct. This guarantees a script always terminates.

**What scripts can and can't do.** They can read `$player` / `$game` (read-only)
and read *and write* `$<variableName>` tracked items. They **cannot** show
messages, address the AI, or write native platform fields — reach for the
dedicated trigger effect for any of those (see
[`fields/TRIGGER_EVENTS.md`](../fields/TRIGGER_EVENTS.md)).

> **Turn-lifecycle note.** Like every trigger effect, a script's writes only
> become visible to the storyteller on the **next** turn — trigger effects run
> at step 9 of the per-turn sequence, after the AI has finished the turn's
> narrative. See
> [`AI_RUNTIME_MECHANICS.md`](./AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
> §3.
>
> That deferral applies to the *storyteller* only. Within the same turn's trigger
> pass, a script's writes **are** visible to everything that runs later — both to
> later scripts and to later triggers' `triggerOnPawScript` *conditions* (Probe D,
> 2026-08-22: `$probe.flag = 1` in trigger 13 made trigger 14's `$probe.flag > 0`
> fire the same turn). Triggers run in **list order**: a consumer placed before its
> producer saw the pre-write state on turn 1 and the new records only from turn 2.
> Order producers before consumers.

---

## 5. Statement set (scripts only)

Scripts add imperative statements on top of the shared expression vocabulary.
Indentation defines blocks (like Python).

### `for each` — bounded iteration

```
for each $puppy in $puppy_tracking_yaml_format_tracked_items
  $puppy.stats.friendliness += 1
```

- The body is the indented block beneath the `for each` line.
- **The loop variable is assignable and writes through to the real item.**
  `$puppy.stats.friendliness += 1` mutates the actual tracked-item entry, not a copy.
- You may only iterate a list, a map, or `range(n)` — never an unbounded source.

### Nested paths — chain dots as deep as the data goes

A YAML tracked item may hold **any valid YAML structure to any depth** (see
[`fields/YAML_TRACKED_ITEMS.md`](../fields/YAML_TRACKED_ITEMS.md) and
<https://infiniteworlds.app/yaml-guide>). PawScript reaches into it by chaining
dots, and a nested path is assignable exactly like a top-level one:

```
$party.leader.stats.hp -= 10          # read-modify-write, three levels down
$puppy.tricks.count()                 # a collection function on a nested list
for each $trick in $puppy.tricks      # iterate a list nested inside a record
  $trick.reliability += 0.05
```

**Depth is free at the script layer.** `$puppy.stats.friendliness` is no more
expensive or fragile to write than `$puppy.friendliness` would be. The cost of
nesting is borne by the *AI* reproducing the shape each turn, not by the script —
so let the data's real structure drive the depth, and use `enforceFormat: true`
with a matching nested `formatSchema` to keep the paths reliably present.

**Writes create; reads don't.** A plain assignment to a missing path **creates**
it — `$subjects.newgirl.suspicion = 7` created the `newgirl` record under an
existing `subjects` map (confirmed 2026-08-22), as did `.item("key") = value` for a
new top-level key. A *read* of a missing path is a hard error:
`set $x = $subjects.ghost.suspicion` rolled the whole script back and logged a
PawScript problem to World Debug. `.exists()` on a missing record returns false
safely.

The distinction is what makes read-modify-write (`+=`, `-=`) the fragile case —
`$party.leader.stats.hp -= 10` reads before it writes, so it fails if `stats` is
missing. Guard reads with `.exists()` or `.item(key, fallback)`, and reserve the
`enforceFormat` argument for items scripts *read* structurally, not merely write to.

Creation is not limited to one level: `$subjects.deep.stats.trust = 1` with both
`deep` and `stats` absent created the whole path, and `set $k = "dyn"` followed by
`$subjects.item($k).suspicion = 1` created a record under a runtime key — both
visible in the tracked-items panel the same turn (Probe D, 2026-08-22).

### `if` / `else if` / `else` — branching

```
if $player_gold >= 100
  $player_gold -= 100
  $has_horse = "true"
else if $player_gold >= 50
  $player_gold -= 50
else
  # not enough gold — do nothing
```

- The condition is a plain expression (§3 / §6). Combine sub-conditions with
  `and` / `or`.

### Assignments

`=`, `+=`, `-=`, and the other compound-assignment operators write to a tracked
item (or an assignable loop variable / `.item(key)` target):

```
$health = 100
$score += 10
$puppy.energy -= 5
```

### `set` — working (scratch) variables

`set` introduces a local scratch variable that lives only for the duration of
the script — handy for accumulating a total or holding an intermediate value
before writing it to a tracked item. A `set` variable is **not** a tracked item
and is **not** persisted.

```
set $total = 0
for each $puppy in $puppy_tracking_yaml_format_tracked_items
  set $total = $total + $puppy.stats.friendliness
$happiness_score = $total
```

It uses the same `$name` form as a tracked-item handle, but is bound locally by
the `set` statement rather than declared as a tracked item. Only writes to real
tracked items (`$happiness_score` above) survive the turn.

### Comments

Lines beginning with `#` are comments and are ignored.

```
# Give every puppy a friendliness bump each turn.
```

### Indentation blocks

Indentation — not braces — delimits the body of `for each` and `if`/`else`.
Keep indentation consistent within a block.

---

## 6. Function & operator cheat-sheet

Functions chain with `.`; some (like `round()`) are top-level. **Brackets mean
"call."** `.count()` counts entries; `.count` (no brackets) reads a field
literally named `count`. This distinction is easy to get wrong.

| Call | Does |
|---|---|
| `.count()` | Number of entries in a list/map |
| `.where(<cond>)` | Filters to entries matching a condition |
| `.item(key)` / `.item(key, fallback)` | Looks up an entry by key; the optional `fallback` is the value returned when the key is missing (a **read** fallback — without it a missing key errors: "add a fallback to cover it"). In scripts, `.item(key)` is also a valid **assignment target**, and assigning to a missing key **creates** it (confirmed 2026-08-22 with a literal key and with a runtime `$k`). |
| `if(cond, then, else)` | Top-level conditional **value** (not the statement form in §5): `if($probe.n > 2, 100, 0)` → `100`. Verified inside a `triggerOnRandomChance` formula (Probe D, 2026-08-22). As a trigger *condition* it never fires — conditions must come out true/false. |
| `.exists()` | Whether the thing exists |
| `.keys()` | The collection's keys |
| `.key()` | The current entry's key (e.g. inside `.format_each(…)`) |
| `.first()` | The first entry |
| `.format_each("…")` | Renders each entry through a template string; supports `{field}`, `{index()}`, `{key()}` placeholders |
| `.join(sep)` | Joins into a string with `sep` between entries |
| `.bulleted_list()` | Renders entries as a bulleted list |
| `.upper()` | Uppercases a string |
| `.append(entry)` | Adds an entry to a list (mutation — scripts only) |
| `.remove(entry)` | Removes a matching entry from a list/map (mutation — scripts only) |
| `.constrain(min, max)` | Clamps a number into the `[min, max]` range |
| `choose(value, case1, result1, case2, result2, …, default)` | Top-level switch: returns the `result` paired with the first `case` equal to `value`, else the trailing `default`. Variadic, as documented on the IW wiki PawScript page (`<<choose($value_to_switch_on, 1, "Instructions 1", 2, "Instructions 2", "Default instructions")>>`). The 4-arg form `choose($probe.n, 3, 100, 0)` is verified inside a `triggerOnRandomChance` formula (2026-08-22). |
| `log(value)` | Writes a value to World Debug for diagnostics (scripts) |
| `round(x)` | Top-level rounding (and similar top-level math) |
| `range(n)` | Top-level: the sequence `0 … n-1` — the bounded source for `for each` |
| `random(…)` / `dice_roll(…)` | Top-level randomness helpers (e.g. dice rolls). Bare `random` is a 0–1 float; `random(1,100)` also returned 0–1 values in the Expression Sandbox (two samples, 2026-08-22) — verify the argument form before relying on its range. |

**Comparison operators:** `=`, `!=`, `<`, `>`, `<=`, `>=`. Equality is a **single** `=`; `==`
is a syntax error ("PawScript compares with a single '='").
**Logical operators:** `and`, `or`, `not`. `or` short-circuits left-to-right: an erroring
right-hand branch is never reached when the left is true, but an erroring **left** branch
kills the whole expression (Probe D, 2026-08-22). A comparison yields text, not a number —
`($x > 2) * 100` errors — so use `if(…)` / `choose(…)` to turn a test into a number.

> **This cheat-sheet is non-exhaustive.** PawScript's full function catalog —
> exact signatures plus additional list/map/number/string helpers — lives in the
> official **Reference** (§7). If you need a capability not listed here, check the
> Reference rather than assuming it doesn't exist.

```
<<puppies.where(friendliness > 5).count()>> puppies love you.
<<puppies.format_each("{name} the {breed}").join(", ")>>
```

---

## 7. Official documentation

The IW platform docs are the authoritative source for PawScript. Cite these
when in doubt:

- **Expressions guide** — https://infiniteworlds.app/pawscript-expressions-guide
- **Script guide** — https://infiniteworlds.app/pawscript-script-guide
- **Reference** — https://infiniteworlds.app/pawscript-reference
- **Expression playground** — https://infiniteworlds.app/pawscript-expression-playground
- **Script playground** — https://infiniteworlds.app/pawscript-playground
- **YAML guide** (structured tracked items) — https://infiniteworlds.app/yaml-guide

---

## 8. Cross-references

- **YAML tracked items** — [`fields/YAML_TRACKED_ITEMS.md`](../fields/YAML_TRACKED_ITEMS.md)
  covers the `yaml` `dataType`, `variableName`, and `formatSchema` /
  `formatExample` / `enforceFormat` — the tracked items PawScript addresses.
- **Tracked items (general)** — [`fields/TRACKED_ITEMS.md`](../fields/TRACKED_ITEMS.md)
  for `dataType` / `visibility` choices and per-turn cost.
- **Trigger effects** — [`fields/TRIGGER_EVENTS.md`](../fields/TRIGGER_EVENTS.md)
  for `effectRunScript` and the other effect types a script can't replace.
- **Template variables** — [`WORLD_JSON_SCHEMA_v2.4.md`](../WORLD_JSON_SCHEMA_v2.4.md#9-template-variable-system)
  §9 for the legacy `<<…>>` interpolation vocabulary.
- **Turn lifecycle** — [`AI_RUNTIME_MECHANICS.md`](./AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
  §3 for when a script's writes take effect.
