# Field Guide: Introducing the Story

Covers: `title`, `description`, `background`, `firstInput`, `objective`.

For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../../WORLD_JSON_SCHEMA_v2.1.md#1-top-level-fields) §1. For broader allocation rules see [`FIELD_ALLOCATION_STRATEGY.md`](../../guidance/FIELD_ALLOCATION_STRATEGY.md).

---

## `title`

**User-facing only. Does NOT influence the storyteller AI.**

The world's name, displayed on the world browser card and at the top of the game interface. Evocative and concise. The platform maintains a separate `version` string for content versioning, optionally auto-incremented via `autoAdvanceVersion`.

---

## `description`

**User-facing only. Does NOT influence the storyteller AI.**

A short blurb shown beneath the title in the world browser. Used by players deciding whether to play. Convey premise, tone, and any content context. Think marketing copy — informative, brief, voice-y.

The AI never sees this. Don't put spoilers or mechanics here.

---

## `background`

**Shown to the player as initial framing. Sent to the storyteller AI every turn — but its effective reach changes after turn 8.**

The initial situation and premise of the story. This field is powerful but **time-limited**: once the Summary AI runs for the first time (turn 8), `background` is absorbed into summaries and the storyteller AI begins seeing the Summary AI's output instead of `background` directly. From turn 8 onward, content that hasn't been re-stated elsewhere is effectively gone from the storyteller's working context.

**What belongs here:**
- The opening world situation — where the player is, what's going on, what kind of story this is.
- Tone-setting information the AI needs from the very first turn.
- The "status quo before the adventure begins."

**What does NOT belong here:**
- Ongoing story developments or evolving state (this field is static after turn 0 — see authoring tactic below).
- Redundant character descriptions — player characters go in `possibleCharacters`; NPCs go in `NPCs`.
- Detailed location or faction lore — use keyword instruction blocks for on-demand injection.

**Authoring tactic.** Write `background` strictly as the situation *at the very beginning* of the story. `background` should remain "evergreen" — sensible reading at turn 50 as much as turn 1.

**Important: `effectChangeBackground` is Start-of-Game (SoG) only.** Confirmed by IW import testing (May 2026): in a regular (mid-game) trigger, IW silently ignores `effectChangeBackground` at runtime. Even if IW allowed it, the effect would be inert mid-game — `background` is only sent to the storyteller AI at turn 0; after ~turn 8 it is superseded by the Summary AI's running summary and the storyteller no longer sees raw `background` text. To change context or setting framing mid-game, use `effectChangeMainInstructions` (replaces the `instructions` block) or restate framing via `summaryRequest`.

For the deeper rule against packing `background` with content that belongs elsewhere, see [`FIELD_ALLOCATION_STRATEGY.md`](../../guidance/FIELD_ALLOCATION_STRATEGY.md#anti-patterns).

---

## `firstInput`

**Single-use hidden prompt. Sent only on turn 0, before the player acts.**

Resembles a player action but is written by the world author. The storyteller AI receives it as if it were the player's first move and writes the initial `outcomeDescription` from it. The player never sees `firstInput` directly — they see only the resulting opening narration.

**What belongs here:**
- The inciting scene-setting action: `"A message arrives on your desk..."`, `"You step off the train into the fog..."`.
- The specific situation the player wakes up into at story start.
- Any opening framing you want the AI to produce as turn 1's narration.

**Can be modified at runtime** via `effectChangeFirstAction` — most useful when the trigger has `triggerOnStartOfGame: true`, where you can vary the opening per player character (`triggerOnCharacter` + `effectChangeFirstAction`).

---

## `objective`

**Displayed to the player from turn 1 onward. Sent to the storyteller AI every turn.**

The player's primary goal. A very powerful tool: the AI receives `objective` every turn with explicit framing that it represents what the player is *trying to accomplish*, and actively steers the story toward satisfying it.

**What belongs here:**
- A clear, directive statement of the player's driving goal.
- A formulation that remains accurate as the story evolves — or be prepared to update it via triggers as phases change.

**Key behaviors:**
- The AI prioritizes `objective` strongly when making narrative decisions. It's the single most powerful lever for shaping the AI's choices about what should happen next.
- **Can be silently swapped mid-game** via `effectChangeObjective`. This is "exceptionally helpful for silently modifying the objective to steer the AI toward elements that might be contrary to the desires of the player character" — useful for corruption arcs, quest progression, loyalty shifts, gradual reveals. The player sees a UI update; the AI sees a new framing for what should drive the narrative.
- Players see the current objective displayed in the UI each turn.

**Authoring tactic.** If your world has multiple story phases or evolving goals, start with the initial objective in this field and wire up `effectChangeObjective` triggers at phase transitions. The transition is seamless — the player sees the new goal appear and the AI's choices realign accordingly.
