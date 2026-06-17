# Character Authoring Guardrails

This document is the discipline contract for writing `possibleCharacters` (player characters) and `NPCs`. It exists to prevent the most expensive failure mode in world authoring: **plausible-sounding fabrication**. A character profile that "feels right" but isn't grounded in any source is harder to repair than a profile that's incomplete.

Read this before writing any character — original creation, modification, or spinoff variant.

---

## 1. The no-citation rule

If you cannot point to a specific source for a detail, do not include that detail.

**Valid sources, in order of strength:**

1. **The author's direct statement.** "Mira is half-elven, wears blue, was a courier before the war." Ask. Confirm. Quote verbatim if helpful.
2. **The source world** (for `modify-world` / `spinoff-world`). What's actually written in `NPCs[*].detail`, `appearance`, `secret_info`, etc.
3. **The story extraction data** (only for sequel workflows — not applicable to the standard new-world workflow).

**Invalid sources:**

- Genre archetypes ("typical rogue appearance," "stern military bearing," "wise old wizard demeanor").
- Inferences from a name ("Victor sounds confident, so he's probably tall and broad-shouldered").
- Patterns from other characters ("the other knights all wear silver, so this one probably does too").
- The agent's own imagination unsupported by author input.

If a detail is missing and you can't get it from the author, **leave the field blank**. An empty `appearance` is honest; a fabricated one is a lie the agent then has to maintain.

---

## 2. Identity and appearance *(canonical `img_appearance` / `img_clothing` rule)*

- **Use the author's own language.** When the author describes how a character looks or speaks, reproduce those phrases. Paraphrasing invites distortion — you'll polish a vivid description into a generic one, or quietly swap one detail for an adjacent one.
- **No genre defaults.** If a character's appearance is never described, leave `appearance` and `img_appearance` empty, or note "not described" in `appearance`. Do not substitute tropes.
- **Distinguish `appearance` from `img_appearance`.** `appearance` is narrative prose the AI uses in `outcomeDescription`. `img_appearance` is image-generation prompt text — it follows different conventions (concrete visual descriptors, comma-separated tags, often LoRA-friendly phrasing). Authors frequently want one but not the other. **Always ask explicitly.**
- **`img_appearance` and `img_clothing` are author input only** *(in new-world / modify-world / spinoff)*. These drive the visual identity of the character via image generation. Wrong text here produces wildly wrong portraits. The agent must not invent these — prompt the author for the actual descriptors they want, even if it means stopping the workflow to ask. **Sequel exception:** the `sequel-world` flow has a story export, which usually narrates appearance; there these fields carry forward from the source world or are synthesized from the story's own description (cited to a turn) before the agent falls back to asking. See the `/infinite-worlds-architect:sequel-world` command's sourcing rules.

---

## 3. Relationships and factions

- **A character being present in a scene is not a meaningful interaction.** Two characters appearing in the same room together does not establish a relationship. Don't infer affection, rivalry, or hierarchy from co-presence alone.
- **Distinguish stated relationships from implied ones.** If the author says "Mira and Daro are siblings," that's stated. If the author says "Mira was raised in the same village as Daro" — that's implied closeness, but the relationship type is unstated. Flag implied relationships as uncertain in `detail` or `secret_info` rather than asserting them.
- **Faction membership without a source is fabrication.** If a character's faction is never stated, leave it blank. Faction allegiance has cascading consequences for trigger logic and NPC interactions; getting it wrong is worse than leaving it ambiguous.

---

## 4. Arc progression and status

- **Quantitative state comes from `trackedItems`, not narrative.** Health, inventory, currency, reputation scores, relationship meters — if the world tracks them via `trackedItems`, the value lives there. Don't restate numeric state in `detail` or `secret_info`; it will fall out of sync the moment the value changes during play.
- **Narrative rationale belongs in `detail` or `secret_info`.** "Why" a relationship broke down, "how" a character reached their current attitude — that's prose, and it lives in the dossier.
- **If an arc is unresolved, say so explicitly.** Don't paper over ambiguity with confident-sounding summary. Write `detail` as past-tense factual narrative ("Mira left the Order after the betrayal at Ravensford") and reserve speculation for `secret_info` ("She may still be in contact with her former mentor — unconfirmed").

---

## 5. When writing characters in `/new-world`

The default failure mode in `new-world` is the agent inventing characters to "fill out" the world before the author has actually decided who they are.

**Mandatory checks before populating any character field:**

1. **Ask, don't infer.** For each character, prompt the author for: name, role in the story, physical description (or "skip"), personality (or "skip"), starting location, anything they should know that the player should not.
2. **Ask separately about images.** "Do you want me to write image-generation prompts (`img_appearance`, `img_clothing`) for this character? If yes, please describe how you want them to look — specific clothing items, hair color, posture, etc." Image prompts are not generated from `appearance` prose by default; they require their own crafted text.
3. **Leave skipped fields blank, not invented.** If the author says "skip personality," the `detail` field can describe role + situation, but must not include personality claims.

For `possibleCharacters`, the same rules apply, plus: the `description` field is shown to the player on the character chooser. Authors usually want a tight, voice-y blurb here — confirm tone before drafting.

---

## 6. When writing characters in `/modify-world`

The default failure mode in `modify-world` is "improving" a character profile by silently embellishing it. Don't.

- **Read the existing dossier first.** Whatever `detail`, `appearance`, `secret_info`, `names`, `img_appearance`, `img_clothing` already contain is the baseline. Confirm with the author before changing or removing any of it.
- **Edits, not rewrites.** If the author asks to "punch up Daro's backstory," ask which specific facets they want to develop. A blanket rewrite loses subtle details (specific phrasings, edge-case names in `names`, hidden hooks in `secret_info`) that the world depends on elsewhere.
- **Watch for `<<template_variables>>` in character fields.** If `description` contains `<<favorite_color>>`, that's a deliberate reference to a tracked item. Don't paraphrase it away.

---

## 7. When writing characters in `/spinoff-world`

Spinoffs inherit a source world's characters. The temptation is to "complete" thinly-sketched source characters by inventing detail. Don't.

- **Source dossiers are the floor, not a starting point to embellish.** If the source world's `NPCs[*].detail` says only "Mira: serves the duke" — the spinoff inherits that limited information. Don't invent her backstory unless the *author* (this is the new author of the spinoff) explicitly provides it.
- **Premise changes don't license character changes.** If the spinoff premise is "same world, 100 years later," the original characters may not even exist in the spinoff. Ask the author which characters carry forward, who replaces whom, and what (if anything) the surviving characters now know.
- **Image prompts often need to change.** Aging, attire shifts, regional variants — `img_appearance` and `img_clothing` are likely to differ between source and spinoff even if the character is "the same person." Re-ask.

---

## 8. Quick checklist

Before considering a character complete:

- [ ] Every claim in `detail`, `appearance`, `secret_info`, `location`, `names` traces to author input or the source world.
- [ ] `img_appearance` and `img_clothing` were author-supplied (or explicitly left blank).
- [ ] `appearance` uses the author's phrasing, not paraphrased generic descriptors.
- [ ] No faction/relationship is asserted that wasn't stated.
- [ ] Numeric state (health, currency, reputation) is in `trackedItems`, not duplicated in the dossier.
- [ ] Unresolved arcs are flagged as such, not glossed.

---

## Cross-references

- **Character field shapes** — `WORLD_JSON_SCHEMA_v2.1.md` §2 (`possibleCharacters`) and §3 (`NPCs`).
- **Where character content does and does not belong** — `FIELD_ALLOCATION_STRATEGY.md` (especially the rule against embedding NPC content in `background`).
- **How character text reaches the AI at runtime** — `AI_RUNTIME_MECHANICS.md`.
