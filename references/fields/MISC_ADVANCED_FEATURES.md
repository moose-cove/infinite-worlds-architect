# Field Guide: Description Request, Summary Request, Evaluation Request

Covers: `descriptionRequest`, `summaryRequest`, `evaluationRequest`, plus the Summary AI lifecycle.

For field shapes see [`WORLD_JSON_SCHEMA_v2.2.md`](../../WORLD_JSON_SCHEMA_v2.2.md#1-top-level-fields) §1.

---

## `descriptionRequest`

**Sent to the storyteller AI every turn. One of the most powerful and important fields available to a world author.**

Controls how the storyteller AI writes its `outcomeDescription`, what it writes into `secretInfo`, and (potentially) how it formats tracked-item updates. The AI interprets and follows these instructions literally — including unusual or very specific directives.

### Default behavior (when empty)

When `descriptionRequest` is empty or `null`, the platform applies its default rules. The fixture's actual stored value documents the platform's default description-writing behavior:

> Briefly describe the immediate results of my action, without any preamble or reminding me of who my character is. Describe any dialogue in full. Describe the physical appearance of any newly introduced characters in detail. Remember that things may go well — or very badly — for my character. Please write your description over several paragraphs.

**Any custom text completely overwrites this default.** If you provide custom instructions, the default text is gone entirely. Include what you need from the default in your custom version if you want to keep those behaviors.

### What you can control

- **Point-of-view and tense.** `"Always write in first-person point of view, present tense, from my character's perspective."`
- **Naming conventions.** `"Never refer to my character by name — always use 'I' or 'me'. Avoid repeating other characters' names more than once per paragraph."`
- **Information placement.** `"Write all mechanical state changes (inventory, relationship shifts, skill effects) into secretInfo, not outcomeDescription."`
- **Structural rules.** `"Begin every response with a one-sentence summary of what happened. Separate dialogue with line breaks."`
- **Style constraints.** `"Never use adverbs. Never begin a sentence with 'I'."`
- **Character introduction rules.** `"When a new character appears, describe their appearance in the first paragraph they appear in."`

### The `secretInfo` pipeline

`descriptionRequest` is the primary mechanism for forcing the AI to write important state information into `secretInfo`. The Summary AI weights `secretInfo` heavily — information written there survives into long-term summaries better than information only in `outcomeDescription`.

Pattern: `"Whenever the player's inventory changes, write the complete current inventory to secretInfo under the key [Inventory]."`

If you find the Summary AI is losing track of important state across summaries, the fix is usually a `descriptionRequest` rule that pushes that state into `secretInfo` every turn.

### Modification at runtime

Use `effectChangeDescriptionInstructions` to replace `descriptionRequest` mid-game — useful for shifting narrative perspective or enforcing new rules at a plot transition. The change persists for the rest of the playthrough until another effect replaces it.

---

## `summaryRequest` and the Summary AI lifecycle

**Read by the Summary AI only. Has no effect on the storyteller AI.**

Directs the Summary AI regarding what to focus on, how to handle character records, what plot threads to track, and the level of detail to maintain.

### When the Summary AI runs

- **First summary: turn 8.** Until turn 8, no summarization happens.
- **Subsequently: every 6 turns** (turn 14, 20, 26, …).
- **Once summarization begins, the storyteller AI's context shifts.** From turn 8 onward, the storyteller no longer sees `background` directly — it sees recent turns of history (typically 2–6) plus the Summary AI's output. This is why `background` is best treated as initial-premise framing only; after turn 8 it's been absorbed into summaries.

### Summary structure

The Summary AI produces:
- A **main summary** — narrative history, max ~1,500 words before condensation is required.
- **Plot threads** — ongoing story arcs the AI is tracking.
- **Character records** — updated NPC dossiers reflecting current state.

### What to put in `summaryRequest`

- **Focus directives.** `"Prioritize tracking the player's relationships with named characters over environmental details."`
- **Character record instructions.** `"Maintain detailed records for all named NPCs. Note any changes in their attitude toward the player."`
- **Appearance consistency.** `"Ensure each character's appearance in their record matches their illustrAppearance and illustrClothes fields."`
- **Plot thread guidance.** `"Always include the player's current objective status as a plot thread."`
- **Condensation rules.** `"When condensing, preserve all numerical state values (gold, health, dates) exactly. Do not paraphrase quantities."`

### Important limitations

- **The Summary AI cannot access `trackedItems`.** State tracked in tracked items is *invisible* to the Summary AI. For important state to survive summarization, write it to `secretInfo` via `descriptionRequest`, or fold it into NPC records the Summary AI maintains. This is the single most consequential limitation of the Summary system.
- **Duplicate character names cause collisions.** If two characters share a name (or very similar names), the Summary AI may merge or confuse their records. The `names` field in `NPCs` helps — ensure character name uniqueness across the world, including alias variants.
- **1,500-word limit** on the main summary. Beyond that, condensation kicks in. Guide the Summary AI explicitly on what to preserve versus what to condense.

### Anti-pattern

Do not instruct the Summary AI to maintain detailed narrative prose. It is meant to track *facts and state*, not recreate the story. Ask for structured records (plot threads, character status, current location, key inventory) — not story recaps. Recaps consume the word budget without preserving the information the storyteller actually needs in future turns.

---

## `evaluationRequest`

**Sent to the storyteller AI every turn. Overrides the default skill-check evaluation system.**

When empty, the platform applies its default evaluation logic (the AI selects a relevant skill, estimates a DifficultyScore, compares against the PC's rating — see [`AI_RUNTIME_MECHANICS.md`](../mechanics/AI_RUNTIME_MECHANICS.md#skill-evaluation-default-model) §5).

Custom text *completely replaces* the default. The platform exposes template variables for use here: `<<skill_list>>`, `<<difficulty_list>>`, `<<skill_example>>`, `<<difficulty_example>>`, `<<skills_and_levels>>` — see [`WORLD_JSON_SCHEMA_v2.2.md`](../../WORLD_JSON_SCHEMA_v2.2.md#1-top-level-fields) §1.

**Common uses:**
- Replace the 0–5 scale with a different rubric (dice rolls, percentage chances, narrative-only evaluations).
- Hide DifficultyScore from the player.
- Decompose complex actions into multi-stage checks.

When overriding the evaluation system aggressively, consider `hideSkillSystem: true` to suppress the platform's default skill UI so it doesn't conflict with the custom logic.
