# Field Allocation Strategy

Where does a given piece of content belong in a world JSON? Player-character description? NPC dossier? Always-on `background`? Keyword-gated `loreBookEntries`? Trigger-gated effect?

Picking the wrong field doesn't break validation — but it does waste context, confuse the AI, and make the world harder to maintain. This document is the decision aid.

Read this before populating `background`, `instructions`, `loreBookEntries`, `instructionBlocks`, or `trackedItems`. Read it again when you find yourself unsure whether a paragraph belongs in `instructions` or as a separate block.

---

## Why allocation matters

Every text field in the world JSON has a different *injection profile* — when, how often, and under what conditions the AI sees it.

- **Always-on fields** (`background`, `instructions`, `objective`, `authorStyle`, `descriptionRequest`, `firstInput`) are sent to the AI **every single turn**. Token cost is paid every turn, forever. Content here had better deserve that cost.
- **Per-character fields** (`possibleCharacters[*].description`, skill list) are sent every turn for the active PC, but only the active PC.
- **NPC dossiers** (`NPCs[*]`) are typically referenced when the NPC is in the scene — they don't all get injected every turn by default.
- **Keyword instruction blocks** (`loreBookEntries[*]`) only inject for 3 turns after a matching keyword appears in recent narrative. Effectively free when irrelevant, present when needed.
- **Extra instruction blocks** (`instructionBlocks[*]`) are always-on like `instructions`, but separable (and modifiable via `effectModifyInstructionBlock`). Use when you want a chunk of always-on text you can swap out by trigger.
- **Trigger-gated content** (`triggerEvents[*].triggerEffects[*]`) only injects when the trigger's conditions fire. The most surgical option for state-dependent content.

**Two failure modes drive most authoring mistakes:**

1. **Packing always-on fields.** Authors paste NPC backstories, location lore, and faction history into `background` because it "feels canonical." The AI now spends tokens re-reading that content every turn — including the 95% of turns where it's irrelevant — and the player pays the cost via inflated prompt sizes and noisier responses.

2. **Treating `background` as state.** `background` is the **initial premise**. `effectChangeBackground` is Start-of-Game (SoG) only — it is silently ignored at runtime in regular (mid-game) triggers (confirmed by IW import testing, May 2026). Even if IW allowed mid-game changes, `background` is only sent to the storyteller at turn 0 and is superseded by the Summary AI after ~turn 8, making a mid-game change inert in any case. For mid-game context shifts, use `effectChangeMainInstructions`. Authors who write running plot summaries into `background` are confused when the AI keeps "rewinding" to early-story framing.

The allocation strategy below exists to push every piece of content to the **least-injecting field that still works**.

---

## The allocation hierarchy

### Always-on (Tier 1)

Populate these for the *minimum* framing every turn needs.

| Field | What belongs here | What does NOT belong here |
|---|---|---|
| `title` | World name | — |
| `description` | User-facing blurb shown in the world browser | Spoilers; mechanics |
| `background` | The initial situation at turn 0 — premise, world state, setting framing (after turn 8, the storyteller views the Summary AI's output rather than raw background — see `INTRODUCING_THE_STORY.md`) | NPC descriptions, location lore, ongoing plot state, post-turn-0 events |
| `objective` | The player's primary goal (one or two sentences) | Sub-goals; conditional goals — use triggers to change `objective` over the course of the story |
| `instructions` | AI decision-making logic — *how to behave*, not *what has happened* | Narrative history; character bios; lore |
| `authorStyle` | Voice, register, prose constraints | Story content |
| `firstInput` | The hidden turn-0 player action that opens the story | — |
| `descriptionRequest` | Rules for how `outcomeDescription` is composed (POV, tense, naming, what to push to `secretInfo`) | Story facts |
| `evaluationRequest` | Override for the skill-evaluation system | — |
| `summaryRequest` | Override for the Summary AI's behavior (every 6 turns from turn 8) | — |

### Per-PC (Tier 2)

| Field | What belongs here |
|---|---|
| `possibleCharacters[*].description` | The selected PC's backstory, personality, and identity — shown on the chooser and used by the AI |
| `possibleCharacters[*].skills` | Per-PC skill ratings (keys must match the world `skills` array) |
| `possibleCharacters[*].initialTrackedItemValues` | Per-character starting values for tracked items |

### NPC dossiers (Tier 3)

NPCs are not always-on — they enter the AI's context when relevant to the scene. Map content to the NPC schema fields:

| NPC field | What belongs here | Notes |
|---|---|---|
| `name` | Display name | — |
| `detail` | Personality, role, motivations, history — the "Character Detail" field | This is the long-form bio |
| `one_liner` | Brief summary shown in the UI | Synthesize from `detail` |
| `appearance` | Free-form physical description | Used by the AI when describing the NPC in narrative |
| `location` | Where the NPC is encountered | — |
| `secret_info` | Info the AI should know but the player should not (hidden motivations, undisclosed identity) | Treated as `secretInfo`-level context |
| `names` | All aliases the character is known by | Drives name-recognition |
| `img_appearance` / `img_clothing` | Image-generation prompt text | **Always ask the author for these — do not invent.** These drive the visual identity of the character and the wrong prompt text produces wildly wrong portraits. |

Do not embed NPC content in `background`. If an NPC is foundational to the world setup, the *fact of their existence* can go in `background` ("You serve under Captain Anjali, a stern woman who tolerates no excuses"), but the NPC's full description goes in `NPCs`.

### Keyword-gated (Tier 4) — `loreBookEntries`

The most token-efficient field type. Each entry has `keywords` (array of trigger phrases) and `content`. Content only injects for 3 turns after a keyword appears in the recent narrative (player action or AI output).

**Use for:**

- **Locations.** Keyword: place name + common variants. Content: setting description, sensory details, hazards. The lore injects when the player enters or speaks of the location, not every turn.
- **Factions / groups.** Keyword: faction name + variants. Content: history, allegiance, internal politics.
- **Situational mechanics.** Keyword: a trigger phrase that signals when the rule applies. Content: the rule.
- **Relationship dynamics.** Keyword: both involved characters' names. Content: the nature of their relationship.

**Do NOT use for:**

- Player character descriptions — those live in `possibleCharacters`.
- NPC descriptions — those live in `NPCs`. Keyword blocks should *supplement* an NPC entry (e.g., "the Order of the Silver Hand" as a keyword block alongside an NPC who's a member), not *replace* it.

### Trigger-gated (Tier 5) — `instructionBlocks` + `triggerEvents`

For content that is only relevant in specific game phases, or that needs to swap out based on player progress:

- **`instructionBlocks[*]`** — Extra always-on blocks. Use when you want a separable chunk of always-on instruction you can later modify via `effectModifyInstructionBlock` (e.g., "Chapter 2 narration rules" replacing "Chapter 1 narration rules").
- **`triggerEvents`** — Conditional logic that fires effects. Use for:
  - Plot-phase transitions (`effectChangeObjective`, `effectChangeMainInstructions`). For mid-game context or setting changes, use `effectChangeMainInstructions` — not `effectChangeBackground`, which is Start-of-Game (SoG) only and silently ignored in regular triggers (confirmed by IW import testing, May 2026).
  - State-dependent AI guidance (`effectTellAIWhatToDo` — one-turn directive, the most reliable steering effect).
  - Hidden information surfacing (`effectGiveInfo` — appended to `secretInfo`, suggestive rather than directive).
  - Tracked item changes (`effectSetTrackedItemValue`).
  - Recurring story beats via `canTriggerMoreThanOnce: true`.

For the full canonical list of v2.2 effect and condition types, see `WORLD_JSON_SCHEMA_v2.2.md` §5.

**Latency implication.** Trigger effects and tracked-item auto-updates
both happen at the end of the turn that triggers them — *after* the AI
has already written the turn's narrative. They influence the AI's
narrative starting on the *next* turn, not the current one. Anything that
needs to take effect immediately must be in the world before the turn
begins — you cannot use a trigger or tracked-item update to react within
the current turn. See
[`AI_RUNTIME_MECHANICS.md`](../mechanics/AI_RUNTIME_MECHANICS.md#3-turn-lifecycle-the-order-matters)
§3 for the full turn lifecycle.

### Author-only (Tier 6)

`designNotes` is **never sent to the AI**. Use it for:

- Author's own implementation notes during world construction.
- The original world-design prompt (the fixture uses it this way).
- TODOs, reminders, future-version planning.

Putting AI-facing content here is a silent no-op — the AI literally never sees it.

---

## Field assignment quick reference

| Content type | Field | Tier |
|---|---|---|
| World title | `title` | 1 (always-on) |
| User-facing blurb | `description` | 1 |
| Initial premise / setting framing | `background` | 1 |
| Player goal | `objective` | 1 |
| AI decision logic | `instructions` | 1 |
| Voice / register | `authorStyle` | 1 |
| Hidden turn-0 prompt | `firstInput` | 1 |
| PC identity + skills | `possibleCharacters` | 2 (per-PC) |
| NPC full dossier | `NPCs` | 3 (situational) |
| Location descriptions | `loreBookEntries` (keyword: place name) | 4 (keyword-gated) |
| Faction / group lore | `loreBookEntries` (keyword: faction name) | 4 |
| Situational rule | `loreBookEntries` (keyword: trigger phrase) | 4 |
| Always-on rule chunk (swappable) | `instructionBlocks` | 5 (trigger-gated swap) |
| Phase-specific narrative rules | `triggerEvents` → `effectChangeMainInstructions` | 5 |
| Plot transition (mid-game) | `triggerEvents` → `effectChangeMainInstructions` / `effectChangeObjective` | 5 |
| Plot transition (SoG only) | `triggerEvents` → `effectChangeBackground` (SoG-only; ignored in regular triggers) | 5 |
| One-turn AI directive | `triggerEvents` → `effectTellAIWhatToDo` | 5 |
| Hidden info for AI only | `triggerEvents` → `effectGiveInfo` (appends to `secretInfo`) | 5 |
| Game state variable | `trackedItems` | varies |
| Author-only notes | `designNotes` | 6 (never AI-visible) |

---

## Anti-patterns

These are the recurring mistakes. Avoiding them is most of the value of this document.

**Do not embed NPC or character descriptions in `background`.** Background is for the initial world premise only. Player character descriptions belong in `possibleCharacters`; NPC descriptions belong in `NPCs`. Location and faction lore belongs in keyword blocks where it injects on-demand.

**Do not put narrative history in `instructions`.** `instructions` is for AI *decision-making logic* — how to evaluate actions, what tone to maintain, what mechanics to enforce. It is not for "what has happened." Use `background` for the initial situation, keyword blocks for character/location lore, and triggers for evolving plot state.

**Do not treat `background` as an ongoing state field.** It holds the world situation at the **very beginning** of the story. `effectChangeBackground` is Start-of-Game (SoG) only — it is silently ignored in regular (mid-game) triggers. For mid-game context or setting changes, use `effectChangeMainInstructions` instead. Only the initial premise and setting belong in `background`; story developments and evolved state belong elsewhere.

**Do not pack always-on fields with content that is only relevant sometimes.** If a piece of content is only useful when the player is in a specific location, talking to a specific NPC, or has reached a specific story phase — that's a keyword block or a trigger-gated effect, not an always-on field. Every always-on token is paid every turn.

**Do not silently discard tracked items when iterating.** If you're modifying a world that already has tracked items, present every existing item to the user before removing any. Items often gate trigger logic in non-obvious ways; deletion has cascading consequences.

**Do not put AI-facing content in `designNotes`.** It will never reach the AI. If you need the AI to see it, it belongs in `background`, `instructions`, an instruction block, a keyword block, or a trigger effect.

---

## Cross-references

- **Schema shapes for every field above** — `WORLD_JSON_SCHEMA_v2.2.md`.
- **Runtime behavior of `instructions` / `descriptionRequest` / `evaluationRequest`** — `AI_RUNTIME_MECHANICS.md`.
- **Anti-hallucination rules when populating characters** — `CHARACTER_AUTHORING_GUARDRAILS.md`.
