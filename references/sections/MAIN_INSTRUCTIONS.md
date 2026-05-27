# Field Guide: Main Instructions, Extra Blocks, Author Style, Design Notes

Covers: `instructions`, `instructionBlocks`, `authorStyle`, `designNotes`, `nsfw`/`mature`, `contentWarnings`.

For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#1-top-level-fields) §1 and §6.

---

## `instructions`

**Sent to the storyteller AI every turn. The highest-cost text field in the world.**

The core block on which all other AI decision-making is built. Establishes setting, tone, mechanics, key rules, and anything the AI must know on every single turn. Every word here is paid for on every turn.

**What belongs here:**
- Core mechanics the AI must apply every turn (skill check rules, evaluation logic, formatting requirements).
- Overarching tone and absolute must-know world rules.
- Constraints on AI behavior that cannot be conditionalized (e.g., "Never break the fourth wall").
- High-frequency formatting requirements (image generation handoff format, HUD format).

**What does NOT belong here:**
- Player character details — auto-injected by the engine from `possibleCharacters[*]`.
- NPC physical descriptions and personality — those go in `NPCs[*]` and are injected situationally.
- Deep lore that only matters in specific situations — use `loreBookEntries` (keyword blocks).
- Trigger mechanics — those auto-fire when their conditions are met.
- Anything that only applies in some turns — redundant context costs tokens every turn.

### The 80/20 efficiency principle

Keep `instructions` lean. The reliable working pattern: ~80% of the token budget goes to truly always-on content (mechanics, tone, mandatory formatting); ~20% can be situational; everything else is offloaded to KIBs or trigger-gated EIBs.

When `instructions` exceeds ~2000 words, profile the content: which lines are read by the AI every turn but only *matter* in some turns? Those are candidates for relocation.

### Prompt engineering tips

- **Use dense, robotic logic over conversational prose.** Strip filler words. "When the player rolls below 3, the action fails" beats "If the player happens to roll a value that is less than 3, then the action should be considered to have failed."
- **Use rigid exclusive language for constraints.** "MUST ONLY contain X", "Exclude all others", "Skip remaining rules". LLMs handle explicit constraints better than implied ones.
- **Make exclusions explicit.** LLMs struggle with implied negative constraints. "Do not narrate beyond the immediate scene" is reliable; "stay focused" is not.
- **Capitalize unconditional rules.** Patterns like "ALWAYS print whereWhen at the start of outcomeDescription" are more reliably followed than lowercased equivalents.

---

## `instructionBlocks` — Extra Instruction Blocks

**Appended after `instructions`. Always-on. Can be modified mid-game via `effectModifyInstructionBlock`.**

Separable blocks of always-on instruction. Each block has `id`, `name`, `content`, and (when `enableAISpecificInstructionBlocks: true` on the world) optional `selectedAIProfiles` to restrict the block to specific AI models.

**Advantages over packing everything into `instructions`:**
- **Swappable.** `effectModifyInstructionBlock` replaces a block's content without touching `instructions`. Use for phase transitions ("Chapter 2 narration rules" replacing "Chapter 1 narration rules").
- **AI-specific variants.** When `enableAISpecificInstructionBlocks: true`, you can send different instruction text to different AI model tiers — cheap models get a simpler ruleset; premium models get a richer one. Reduces cost without dumbing down the experience for premium users.
- **Modular.** Easy to update one section without rewriting the whole `instructions` block.

**When to use an EIB instead of `instructions`:**
- Any always-on content you expect to swap mid-game.
- Model-tier-specific variants of the same conceptual rule.
- Conceptually-discrete rule chunks that benefit from being independently labeled.

---

## `authorStyle`

**Sent to the storyteller AI every turn. Controls voice and writing style.**

Defines how the AI writes `outcomeDescription` — the writing style, tone, narrative perspective, genre register. The AI adopts the role and approach the field implies.

**What belongs here:**
- Writing style descriptor: `"Gritty noir detective fiction"`, `"Whimsical fairy tale"`, `"Clinical psychological horror"`.
- Narrative person and tense (if not enforced by `descriptionRequest`).
- Author persona: `"You are a master storyteller in the style of Ursula K. Le Guin"`.
- Stylistic rules the AI should follow consistently.

**Power technique.** Explicitly stating *AI capabilities* in `authorStyle` shifts the AI's behavior measurably. `"You excel at tracking numerical state changes precisely"` makes the AI more careful with numbers. `"You are an expert at maintaining consistent character voices across dialogue"` improves dialogue fidelity. The AI tends to "live up to" capabilities asserted in the prompt.

**Can be replaced mid-game** via `effectChangeAuthorStyle` — useful for genre transitions or deliberate tonal shifts at plot points.

See [`AI_RUNTIME_MECHANICS.md`](../AI_RUNTIME_MECHANICS.md#6-author-style-guidelines) §6 for additional author-style discipline (consistency, model-tier proactivity, descriptive depth placement).

---

## `designNotes`

**NEVER sent to the AI. Author-only scratchpad.**

A free-form field for the world author: original design prompts, implementation notes, design intentions, TODOs, reminders. Completely excluded from AI processing.

**Use freely.** There is no token cost. Be honest with yourself in this field — if you write "I'm not sure if the magic system works, revisit if it feels off in playtesting", future-you (or a collaborator) will thank you.

**Common anti-pattern.** Authors sometimes treat `designNotes` like a comment field that the AI will read for context. It will not. If you need the AI to see it, it belongs in `background`, `instructions`, an instruction block, a keyword block, or a trigger effect — not `designNotes`.

---

## `mature` and `nsfw`

**Platform categorization flags. Do NOT control AI behavior.**

- `mature: true` — R-rated content (violence, suggestive material, mature themes but not explicit sex).
- `nsfw: true` — X-rated content (explicit sexual content). **`nsfw: true` implies `mature: true`** — a world cannot be `nsfw` without also being `mature`.

Both are thematic-sorting flags for the platform's world browser. They do *not* change how the storyteller AI behaves during play. AI content behavior is controlled via `instructions` and `authorStyle`.

---

## `contentWarnings`

**Comma-separated string. Displayed to the player as an acknowledgement prompt before gameplay begins.**

Examples: `"graphic violence, non-consensual situations, substance abuse"`. Purely a player-facing disclosure mechanism — no effect on AI behavior.

Use this for ethical disclosure (themes a sensitive player might want to know about in advance), not for thematic flavor.
