# Field Guide: Player Characters and Permissions

Covers: world-level `skills`, the `possibleCharacters` array, and the six `allowChangeCharacter*` permission booleans.

For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#2-possiblecharacters-player-characters) §2 and §7.

---

## `skills`

**Array of skill name strings. Sent to the storyteller AI every turn.**

A list of attributes the storyteller AI uses to evaluate player actions. The AI selects relevant skill(s) from this list and applies them when assessing whether a player's action succeeds or fails.

### The 0–5 scale

| Rating | Label |
|---|---|
| 0 | Incapable |
| 1 | Incompetent |
| 2 | Unskilled |
| 3 | Competent |
| 4 | Highly Skilled |
| 5 | Exceptional |

(See [`AI_RUNTIME_MECHANICS.md`](../AI_RUNTIME_MECHANICS.md#skill-evaluation-default-model) §4 for how the AI uses this scale at runtime.)

### Requirements and conventions

- **At least 1 skill is required** to run a world.
- **Typical worlds have 3–5 skills.** More than 7 dilutes the AI's selection — it will often pick a less-relevant skill when the relevant one is buried among many.
- **No per-skill description field.** There is no way to explain what a skill does beyond its name in the `skills` array itself. If you need to explain what a skill covers or how it works, put that explanation in `instructions`.

**Naming tip.** Use clear, self-describing skill names the AI can interpret without extra context: `Persuasion`, `Stealth`, `Combat`, `Hacking`, `Empathy`. Avoid cryptic or world-specific names without explaining them in `instructions`.

**Template-variable generation.** Each skill name automatically becomes a template variable: `Persuasion` → `<<skill_persuasion>>`, `Hacking` → `<<skill_hacking>>` (lowercase, spaces become underscores). Use these in `instructions` and trigger conditions to reference skill ratings.

---

## `possibleCharacters`

**Each character's data is sent to the storyteller AI every turn — for the selected character only.**

An array of player character options shown on the chooser. At least 1 character is required. Worlds typically offer 3–4 options.

**Critical:** Only the *selected* character's information passes to the AI. Unselected character definitions are invisible to the AI during play. If you want a character to exist regardless of player choice — e.g., an NPC that's also a possible PC — list them in `NPCs` as well.

### Sub-fields

**`name`**
The identifier passed to the storyteller AI. Used to avoid accidentally naming other characters the same thing. Can be modified mid-game via `effectChangePCName`.

**`description`**
Physical appearance, personality traits, plot hooks, and any related information. **Passed to the AI every turn, so it always influences the AI's decisions.** Write it as the AI's reference for who this character is at all times — not just at game start. Can be modified via `effectChangePCDescription`.

**`portrait`** *(platform-managed)*
Optional image for the character selection screen. **Important:** Built-in portrait generation prompts are not saved and do not affect in-game illustration prompts. For consistent character appearance in gameplay images, describe the character in `description` and/or add them to `NPCs` (with `img_appearance`/`img_clothing` populated).

**`skills`**
The character-specific skill ratings mapping, e.g. `{"Strength": 4, "Stealth": 2}`. Keys must match the world-level `skills` array exactly. The AI uses these ratings when evaluating the character's actions.

**Player constraint note.** It is impossible for a player to distribute more than the original total skill value. Players can only redistribute (with `allowChangeCharacterSkills: true`), not inflate, their skill total.

**`initialTrackedItemValues`**
Per-character starting values for tracked items. Each entry: `{id, name, visibility, initialPCValue, initialValueBasedOnPC}`. The `initialPCValue` may be a string OR a string array — when an array, it represents the *set of choices* the player picks from at character selection. Treat the array as an unordered set, not a `[min, max, default]` tuple.

**`portraitPromptDetails`** *(hybrid)*
Author-provided prompt info used to generate the portrait. Same shape as the world-level `imagePromptDetails`. See [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#8-image-prompt-details-world--per-character) §8.

---

## Player permissions

Six top-level booleans control what the player can customize before starting the adventure. Note that v2.1 uses `allow*` field names (not the older `can*` form):

| Field | Default | What it allows |
|---|---|---|
| `allowChangeCharacterName` | `true` | Player may rename their selected PC |
| `allowChangeCharacterDescription` | `true` | Player may edit their selected PC's description |
| `allowChangeCharacterSkills` | `false` | Player may redistribute skill points (total cannot increase) |
| `allowChangeCharacterItemValues` | `false` | Player may change per-character starting tracked-item values |
| `allowChangeCharacterPortrait` | `false` | Player may select an alternate generated portrait |
| `allowChangeCharacterNewPortrait` | `false` | Player may generate a new portrait |

**Authoring guidance.** Defaults are reasonable for most worlds.

- Lock skill redistribution (`allowChangeCharacterSkills: false`, the default) for worlds where specific skill loadouts are essential to intended difficulty or balance.
- Enable `allowChangeCharacterItemValues: true` only if starting values are meant to be player-configurable (e.g., a "point buy" mechanic).
- The portrait permissions default `false` because most authors prefer to control the character's visual identity. Flip them only when the visual identity is genuinely player-driven.
