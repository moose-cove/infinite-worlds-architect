# Pattern: Expression-Switched Instructions (lag-free mode switch)

> **Provenance:** Play-observed, on thin evidence: one hand-played run of Probe F
> (2026-09-30), one turn per mode, and no World Debug capture of the rendered block. The
> operator saw an extra instruction block built from a PawScript expression follow a
> tracked item's new value on the very next turn. The result assumes `hidden` item values
> are not sent to the AI, which is documented but not yet checked at runtime. See
> [`probes/README.md`](../../probes/README.md#answered-by-probe-f-2026-09-30-played).

---

## What it does

An extra instruction block (EIB) holds a `<<choose(…)>>` expression instead of fixed text.
The expression picks one instruction variant based on a tracked item's current value. When
that value changes, the block the AI receives changes with it. No trigger is involved.

Use it when an instruction should always follow a tracked item's **current** value, and
especially when the **player** controls that value. Typical uses: a player-selectable
narration style, difficulty, point of view, content intensity or pacing mode.

## Why it beats trigger-driven swapping

Trigger effects run at step 9 of the turn lifecycle, after the AI has already written the
turn (see [`AI_RUNTIME_MECHANICS.md`](../mechanics/AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
§3). Suppose the player changes a mode item between turn N and turn N+1:

| Route | When the gate sees the edit | First turn written under the new mode |
|---|---|---|
| **Expression in the EIB** (this pattern) | Not applicable: the prompt for turn N+1 is built from the new value | **Turn N+1** |
| Trigger (`triggerOnPawScript` on the mode item → `effectModifyInstructionBlock`) | Step 9 of turn N+1, after the AI has written that turn | Turn N+2, one turn late |

The trigger row follows from the documented lifecycle; Probe F had no trigger arm. Probe F
observed the expression row:
the player switched the mode between turns, and the very next turn followed the new
variant.

The pattern is also simpler. Switching back and forth takes no extra triggers, needs no
`canTriggerMoreThanOnce` bookkeeping, and cannot leave the block stuck on a stale variant
when a one-shot trigger has already fired.

When the **AI** updates the item instead (via `autoUpdate` and `updateInstructions`), the
update is proposed at step 7 and applied at step 9 of turn N. The expression and a trigger
then both reach the AI on turn N+1, as long as the watching trigger sits after anything that
changes the item in `triggerEvents` order (otherwise the trigger lands on N+2). In that
case the gain is simplicity and order-independence, not timing.

## Template

The switch is a player-visible item. Each instruction variant lives in its own `hidden`
item, and the EIB selects between them:

```json
"trackedItems": [
  {
    "id": "NarrModeX",
    "name": "Narration Mode",
    "variableName": "narration_mode",
    "dataType": "text",
    "positionInList": 0,
    "visibility": "everyone",
    "autoUpdate": false,
    "initialValue": "Cinematic",
    "updateInstructions": "Never change this value. Only the player edits it.",
    "description": "Cinematic or Terse. Edit this to change how the story is narrated."
  },
  {
    "id": "NarrCinem",
    "name": "Narration Cinematic",
    "variableName": "narration_cinematic",
    "dataType": "text",
    "positionInList": 1,
    "visibility": "hidden",
    "autoUpdate": false,
    "initialValue": "Narrate in long, sensory, cinematic paragraphs with lingering camera-like detail.",
    "updateInstructions": "Never change this value.",
    "description": "Instruction text for Cinematic narration."
  },
  {
    "id": "NarrTerse",
    "name": "Narration Terse",
    "variableName": "narration_terse",
    "dataType": "text",
    "positionInList": 2,
    "visibility": "hidden",
    "autoUpdate": false,
    "initialValue": "Narrate in two or three short, plain paragraphs. No lingering description.",
    "updateInstructions": "Never change this value.",
    "description": "Instruction text for Terse narration."
  }
],
"instructionBlocks": [
  {
    "id": "NarrInstr",
    "name": "Narration Mode Instructions",
    "content": "Current narration mode: <<narration_mode>>.\n<<choose($narration_mode, \"Cinematic\", $narration_cinematic, \"Terse\", $narration_terse, \"Narration mode not recognised - use Cinematic narration.\")>>"
  }
]
```

(Optional tracked-item fields are omitted for brevity; `name`, `positionInList`,
`dataType`, `visibility` and `autoUpdate` are required. Mint real IDs with `mint_ids`.)

The `Current narration mode: <<…>>` echo line is optional. It shows the live value in the
rendered block, which makes a failed match easy to spot in World Debug.

## Why the variants live in `hidden` tracked items

- **The AI only receives the selected variant.** Per the documented `hidden` semantics, a
  hidden item's value is not sent to the AI directly. An expression that reads it delivers
  the value: in Probe F the variant rule texts existed only in `hidden` items, and the AI
  obeyed whichever one was selected. With `ai_only` or `everyone` items, the AI would see
  every variant every turn and pay tokens for all of them.
- **No nested quoting.** Long instruction text written as string literals inside `choose`
  would need escaping twice, once for PawScript quotes and again for JSON. A tracked item
  holds plain text.
- **Editable in the world editor.** Each variant is an ordinary tracked-item value.

For short variants, inline literals are fine:
`<<choose($pace, "Slow", "Take your time.", "Fast", "Keep scenes brisk.", "Keep scenes brisk.")>>`.

## Rules and pitfalls

- **Use the `$variable_name` form inside the expression.** `choose` compares the value to
  each case with equality. Write `$narration_mode`, not a nested `<<narration_mode>>`. In
  trigger gates, `<<…>>` is substituted as text before parsing and breaks non-numeric
  comparisons (see [`PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md) §3). That was probed on
  `triggerOnPawScript`, not inside a `<<choose(…)>>`, but it likely fails the same way.
- **Always end with a default.** `choose` returns the trailing default when no case matches.
  Make the default a safe instruction, or a message naming the problem, never an empty
  string. A player who types `terse` instead of `Terse` gets the default: whether text
  equality ignores case is unverified. Spell the accepted values out in the switch item's
  `description`.
- **Set `autoUpdate: false` on every item involved.** The switch belongs to the player, and
  the variants are fixed text. Neither should be rewritten by the AI.
- **The switch item must be player-visible.** When the harness mapped the in-game
  tracked-item editor on 2026-09-30, it listed the `everyone` item and did not offer the
  `hidden` ones. Probe F used `everyone`. `player_only` might also work and would keep the
  raw value out of the AI's context (drop the echo line too), but that is untested. So is
  whether the editor needs Storyteller mode;
  [`TARGET_WORD_COUNT.md`](TARGET_WORD_COUNT.md) assumes the player edits in Storyteller
  mode.
- **A broken expression leaves no sign in the story text.** A malformed expression is
  documented to render nothing (see [`PAWSCRIPT.md`](../mechanics/PAWSCRIPT.md) §3), though
  it may show as the literal tag; either way the `choose` line stops doing its job. How an
  unknown `$name` renders in an EIB is untested. Check the rendered block in World Debug
  under "Instructions sent to the AI" (see
  [World Debug Tools](../mechanics/PLATFORM_BEHAVIOR_NOTES.md#world-debug-tools) for how to
  open it).
- **Don't test it on the opening turn.** In the operator's experience the opening turn
  almost always ends with the objective line, whatever an "end the turn with X" style
  instruction says; Probe F's opening turn did. Judge from the first regular turn onward.

## Variants and neighbours

- **More than two modes:** add more case/result pairs to `choose`.
- **Numeric thresholds:** use `if(…)`, e.g.
  `<<if($danger_level > 5, $danger_high, $danger_low)>>`. `if(…)` is verified as a value
  inside chance formulas, but Probe F only confirmed `choose` inside an EIB, so check the
  rendered block in World Debug.
- **[`TARGET_WORD_COUNT.md`](TARGET_WORD_COUNT.md)** uses the same mechanism with arithmetic
  instead of `choose`. A player's edit to the word count should reach the next turn in the
  same way (inferred; Probe F tested `choose` in an EIB).
- **[`PHASE_ESCALATION.md`](PHASE_ESCALATION.md)** (trigger-driven EIB replacement) is still
  the right tool when the change comes from an AI-judged story beat, or when it must be a
  one-way transition. If the phase is fully determined by a tracked item's value, prefer
  this pattern: it has no lag and is reversible.
