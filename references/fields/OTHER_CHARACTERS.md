# Field Guide: NPCs (Other Characters)

JSON key: `NPCs` — array of NPC objects. For field shapes see [`WORLD_JSON_SCHEMA_v2.4.md`](../../WORLD_JSON_SCHEMA_v2.4.md#3-npcs) §3.

For the discipline of writing characters without fabricating, see [`CHARACTER_AUTHORING_GUARDRAILS.md`](../guidance/CHARACTER_AUTHORING_GUARDRAILS.md).

---

## How the engine uses NPCs

NPCs populate the game's **character database** at startup. This database is not modified mid-game by edits to `NPCs` — changes to the world JSON after the game starts don't affect an in-progress session.

The **Summary AI** (runs every 6 turns from turn 8) updates NPC records as the game progresses, incorporating new information about characters from recent context. The runtime NPC state thus drifts from the world JSON's `NPCs` definitions as play continues.

---

## NPC field reference

### `one_liner` (Brief Summary)

**The only NPC field visible to the storyteller AI until the turn after the character (or their location) is first mentioned.**

Every other NPC field — `detail`, `appearance`, `location`, `secret_info` — is invisible to the storyteller AI until the character appears in the story. This makes `one_liner` the **most important NPC field to get right**.

**What belongs here:**
- The highest-signal facts about this character: role, defining personality trait, one distinctive physical feature, relationship to the player.
- Written for the AI's benefit, not the player's. Dense, useful, not stylistic.
- Examples:
  - `"Veteran detective, cynical but fair, short-cropped grey hair. The player's reluctant partner."`
  - `"The café owner who knows everyone's secrets — warm on the surface, calculating underneath."`

**Length guidance.** Keep it under 100 words. `one_liner` is injected every turn once the character has appeared, so treat it like the NPC-equivalent of `instructions` — every word costs tokens forever.

### `detail` (Character Detail)

**Loaded after the character is first mentioned. Comprehensive character development.**

The primary section for backstory, personality depth, motivations, history, speech patterns, character arc. Only loaded by the AI after the character enters the scene, so it can be much more expansive than `one_liner` without wasting tokens.

This is where the rich character writing goes.

### `appearance`

**Warning: The storytelling AI frequently ignores this field.**

Physical description for the storyteller AI's narrative use. Do not rely on `appearance` for narrative consistency — if consistent appearance is critical, restate key details in `one_liner` or `instructions`.

Use `img_appearance` for **image generation** consistency — that system is independent and more reliable than the storyteller AI's adherence to `appearance` text.

### `location`

The setting where the character should first appear. Guides the AI's initial placement of the character in the scene. Can be a place name, a description, or a situational context (e.g., `"the smoky back room of the Crow's Foot Tavern"`).

### `secret_info` (Secret Information)

> **Note:** This NPC field is named `secret_info` (snake_case) and is part of the world's authored NPC dossier. It is distinct from the runtime output field `secretInfo` (camelCase) that the storyteller AI emits each turn. Both contribute to "info the player doesn't see," but they live in different fields with different lifecycles.

**Carries less influence on the AI than the other sections.**

Background details hidden from the player but available to the AI for story consistency. The Summary AI weights `secretInfo`-derived information heavily during summarization. Good for: hidden motivations, secret relationships, information the player may eventually discover.

Not a strong enforcement mechanism — the AI may not act on `secret_info` reliably. If a fact in `secret_info` needs to actually drive AI behavior, restate it in `instructions` or fire it as `effectGiveInfo` when relevant.

Leave blank if there are no secrets.

### `names` (string[])

**Prevents the AI from treating different name forms as separate characters.**

Include all name variants the character is known by: full name, nicknames, titles, how they're addressed in dialogue. Example: `["Dr. Sharon Stone", "Dr. Stone", "Sharon Stone", "Sharon", "Doc"]`.

If omitted, the AI may create separate runtime character records for "Dr. Stone" and "Sharon" as if they were two different people. The Summary AI will then maintain divergent records for what is conceptually one character. Always populate this field if a character has any name variants.

### `img_appearance` and `img_clothing`

**For the image generation AI, not the storyteller AI.**

These feed the image generation system's character portrait prompts. Since image AI and storyteller AI are independent, explicit appearance details here are more reliably applied to generated images than `appearance` is to narrative text.

- `img_appearance`: Physical description formatted for image generation (age, hair, eyes, skin tone, build). Concrete visual descriptors, comma-separated tags, LoRA-friendly phrasing.
- `img_clothing`: Current clothing description (exclude footwear by standard image generation convention).

**These fields typically require author input and must not be invented.** If the source material doesn't describe the character's appearance, prompt the user to confirm or supply these values. See [`CHARACTER_AUTHORING_GUARDRAILS.md`](../guidance/CHARACTER_AUTHORING_GUARDRAILS.md#2-identity-and-appearance) §2.

---

## Authoring checklist

- [ ] `one_liner` is dense, high-signal, and under 100 words — it's the only thing the AI sees until the character appears.
- [ ] `names` includes all name variants to prevent character identity fragmentation.
- [ ] Critical appearance details are in `one_liner` (not just `appearance`) if narrative consistency matters.
- [ ] `img_appearance` and `img_clothing` are confirmed by the author, not invented.
- [ ] `detail` contains the full backstory and personality — this can be rich and expansive.
- [ ] `secret_info` is left blank when there are no actual secrets (don't fabricate to fill the field).
