# Field Guide: Keyword Instruction Blocks (`loreBookEntries`)

JSON key: `loreBookEntries` — array of keyword block objects. Each entry has `id`, `name`, `keywords` (string[]), `content`. For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#6-instruction-blocks) §6.

---

## What keyword blocks do

KIBs are conditional instruction blocks delivered to the storyteller AI only when specific keywords appear in recent context. They act like "Lore Books" — invisible until triggered, then injected into the AI's context for a window of turns.

**The AI has zero awareness of a KIB's existence until it is triggered.** The AI cannot reference, hint at, or be aware of content in an unfired KIB. This is by design — unfired blocks cost zero tokens.

---

## Keyword matching mechanics

**Substring match, case-insensitive.** Keywords are matched by simple string comparison:
- The keyword `"hat"` will match "whatever", "chatter", "hatchet" — any word *containing* that letter sequence.
- The keyword `"magic"` will match "magical", "magician", "magic".
- Case does not matter: `"Dragon"` matches "dragon", "DRAGON", "A Dragon Appears".

This is the most important and most easily forgotten fact about keyword blocks. A naïvely-chosen keyword like `"art"` will match every appearance of *part*, *start*, *heart*, *artery*, *parties*, etc. — flooding the AI with the block on every turn.

**What triggers matching:**
- Keywords found in the **player's input** → block activates for that turn's AI response.
- Keywords found in the **AI's output** → block activates for the **following** turn.

**Injection window.** Once triggered, the KIB content remains active for **the next 3 turns** regardless of whether the keyword continues to appear.

---

## The awareness paradox

Because the AI has no awareness of a KIB until it fires, there is a design challenge: **if a topic is never mentioned, the KIB that covers it will never activate**.

For topics that might never organically surface, you may need a brief mention in `instructions` to ensure the AI references the topic when appropriate. Example: include "The ruins of Valdrath are accessible from the western forest path" in `instructions` even if the full Valdrath lore is in a KIB — this creates an *entry point* for the keyword "Valdrath" to appear naturally.

This is the keyword-block author's most common blind spot. A beautifully detailed KIB for a faction the AI never spontaneously mentions is a KIB that never fires.

---

## What to put in KIBs

**Ideal use cases:**
- **Deep world lore.** History, faction backgrounds, magic system mechanics.
- **Location descriptions.** What a place looks, sounds, smells like.
- **Conditional mechanics.** Rules that only apply in specific situations (e.g., underwater combat rules only when underwater).
- **Character-specific context.** Detailed dossiers on characters the player may never meet.
- **Optional content** players may never encounter.

**Not suited for KIBs:**
- **High-frequency content.** If the keyword appears constantly (e.g., character names, the word "I"), the block is always injected and you pay for it every turn. Use `instructions` or Extra Instruction Blocks instead.
- **Content the AI needs from turn 1.** Use `instructions` or `background` for always-needed framing.
- **Player character or main NPC descriptions.** Those have their own dedicated fields (`possibleCharacters[*].description`, `NPCs[*]`).

---

## Keyword design guidelines

- **Include synonyms, related concepts, and likely misspellings:** `["magic", "spell", "casting", "mana", "sorcery"]`.
- **Use multi-word phrases for precision** when single words would over-trigger: prefer `["haunted forest", "the forest of shadows"]` over just `["forest"]` if the world has multiple forests.
- **Keep keywords specific enough to be discriminating.** A keyword that fires on common English words is a token leak.
- **First keyword becomes the display name.** The first entry in `keywords` is what shows up in the platform UI as the block's title. Order accordingly.
- **Keep content hyper-focused and bulleted.** KIB content injects mid-narrative; clarity matters more than prose flow.

---

## Modification by triggers

Both keyword blocks and Extra Instruction Blocks can be modified mid-game via trigger effects:

| Field array | Modifying effect | Replaces |
|---|---|---|
| `loreBookEntries` (KIBs) | `effectModifyKeywordBlock` | Both `keywords` and `content` of the target block by `id`. |
| `instructionBlocks` (EIBs) | `effectModifyInstructionBlock` | The `content` of the target block by `id`. |

This is how you implement "the player learns a new technique" or "the village now has a different mood" — change the KIB's content via trigger, and from that point forward (with the standard injection window delay) the new content is what gets injected when the keyword fires.

---

## Keyword Blocks vs. Extra Instruction Blocks

| Feature | Keyword Blocks (`loreBookEntries`) | Extra Instruction Blocks (`instructionBlocks`) |
|---|---|---|
| Activation | Keyword match in recent context | Always-on (modifiable via trigger) |
| Token cost | Zero until triggered | Every turn |
| Best for | Conditional / optional lore | Core mechanics, phase-specific instructions |
| Modified by | `effectModifyKeywordBlock` | `effectModifyInstructionBlock` |
| AI awareness when inactive | None | N/A (always active) |

If the content is relevant every turn → EIB or `instructions`. If it's relevant only when a specific topic surfaces → KIB.

See also: [`FIELD_ALLOCATION_STRATEGY.md`](../FIELD_ALLOCATION_STRATEGY.md) on the broader always-on vs. keyword-gated vs. trigger-gated decision.
