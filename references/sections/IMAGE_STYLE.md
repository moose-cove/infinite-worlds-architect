# Field Guide: Image Style

Covers: `imageModel`, `imageStyle`, the four `imageStyleCharacterPre/Post` and `imageStyleNonCharacterPre/Post` wrapper fields, and the newer `illustrationStyleCharacterHighPriority`/`LowPriority` and `illustrationStyleNonCharacterHighPriority`/`LowPriority` fields.

For field shapes see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#1-top-level-fields) §1 and §8 (per-character `portraitPromptDetails`).

---

## Scoping note

Image style settings control the **image generation AI only**. They have no influence on how the storyteller AI generates its narrative outputs. The two AI systems are entirely independent — getting one right doesn't affect the other.

A common confusion: authors who write detailed `appearance` text in `NPCs` expect that to drive the character's portrait. It does not. The portrait is driven by `img_appearance` and `img_clothing` on the NPC, plus the world-level wrapper fields below.

---

## `imageModel`

The image generation model. Two categories:

**Natural-language models** (accept descriptive prose):
- `flux.1-schnell` — Flux model. ~300-word prompt limit before elements get silently dropped.
- `manticore` — Manticore model. ~400-word prompt limit. Supports Manticore-specific LoRA keywords.
- `wyvern` — Wyvern model. Natural language.

**Tag-based models** use priority tag lists rather than prose; limited space for descriptive content.

For most worlds, `manticore` or `flux.1-schnell` are the standard choices.

---

## `imageStyle`

A style descriptor string passed to the image model. Examples: `photo_beautiful`, `photo_1`, `oil_painting`, `anime_detailed`. Manticore accepts custom style definitions; Flux and Wyvern have preset options. The fixture often shows values like `"photo_1"`.

---

## Wrapper fields (Pre/Post)

Four legacy wrapper fields wrap the AI-generated image subject description with author-supplied prefix/suffix text:

**Wrap order.** The platform constructs the image prompt as:
`<Pre field text> + <AI-generated subject text> + <Post field text>`. The
Pre fields appear at the beginning of the image prompt; the Post fields at
the end. Order accordingly when choosing what goes where (LoRA triggers
typically work best toward the end).

| Field | When used |
|---|---|
| `imageStyleCharacterPre` | Prepended before character image descriptions |
| `imageStyleCharacterPost` | Appended after character image descriptions |
| `imageStyleNonCharacterPre` | Prepended before scene/setting image descriptions |
| `imageStyleNonCharacterPost` | Appended after scene/setting image descriptions |

**What goes in these fields:**
- **Pre** (prompt beginning): Style keywords, quality modifiers, genre tags. `"masterpiece, professional photography, cinematic lighting"`, `"oil painting, impressionist style, vibrant colors"`.
- **Post** (prompt ending): LoRA trigger keywords, technical quality tags, negative-prompt guidance. `"IWUpscaleFace, IWBeautiful"`, `"IWAnime"`.

---

## Newer `illustrationStyle*` fields

v2.1 introduced four parallel fields that coexist with the older `imageStyle*Pre/Post` fields:

- `illustrationStyleCharacterHighPriority` / `LowPriority`
- `illustrationStyleNonCharacterHighPriority` / `LowPriority`

The exact precedence rules between the newer `illustrationStyle*` fields and the older `imageStyle*` fields are unverified — both sets may be present on the same world. Preserve all values on round-trip. When authoring new style content, the safest pattern is to populate the newer fields and leave the older ones empty (or copy the same content into both) until precedence is documented.

---

## LoRA keywords

**Flux-specific:**
- `IWDefault` — default Flux style
- `IWClassic` — classic Flux style
- `IWAnime` — anime art style
- `IWRemoveNudityWordsWhenNoNudity` — sanitizes prompt when the nudity flag is off

**Manticore-specific:**
- `IWUpscaleFace` — face quality improvement with upscaling
- `IWUpscaleFaceSmooth` — upscaling with smoothing applied
- `IWBeautiful` — general beauty enhancement
- `IWBeautiful2` — alternative beauty enhancement variant

Drop these into the Post field for the relevant subject type. The model recognizes them as activation keywords and applies the corresponding LoRA weight.

---

## Authoring techniques

**Style fusion.** Combine artist styles for unique aesthetics: `"mixture of Vincent van Gogh and Banksy"`, `"blend of art nouveau and cyberpunk"`. The model interpolates between the named styles' learned distributions.

**Layered descriptions for scenes.** Structure non-character prompts by depth: `"layer 1 (foreground): cobblestones and puddles; layer 2 (midground): gas lamps and fog; layer 3 (background): gothic spires"`. Gives the image AI a spatial composition framework rather than a flat tag list.

**Word-limit awareness.** Stay within model limits (Flux ~300w, Manticore ~400w). Prompts that exceed the limit have elements dropped *unpredictably* — prioritize the most important style descriptors at the beginning of the wrapper fields.

**Character consistency requires per-character work.** The world-level image style fields alone cannot ensure consistent character appearance across scenes. For character consistency:
- For player characters: detailed `possibleCharacters[*].description` plus `portraitPromptDetails` (the per-character version of the world-level `imagePromptDetails` — see [`WORLD_JSON_SCHEMA_v2.1.md`](../WORLD_JSON_SCHEMA_v2.1.md#8-image-prompt-details-world--per-character) §8).
- For NPCs: `img_appearance` and `img_clothing` on the NPC. Always ask the author for these — see [`CHARACTER_AUTHORING_GUARDRAILS.md`](../CHARACTER_AUTHORING_GUARDRAILS.md#2-identity-and-appearance).
