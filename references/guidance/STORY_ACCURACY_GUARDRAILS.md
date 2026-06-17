# Story Accuracy Guardrails

This document is the no-fabrication discipline contract for **sequel-world** authoring. It extends the character-level guardrails in [CHARACTER_AUTHORING_GUARDRAILS.md](./CHARACTER_AUTHORING_GUARDRAILS.md) to cover all world fields shaped by story export data.

Read this before proposing any field value in a `sequel-world` flow.

---

## 1. Core principle: the export is the evidence floor

When building a sequel world, the story export is the primary source of truth for what actually happened. The agent's job is to surface that evidence and let the author decide how to translate it into sequel world structure — not to fill gaps with plausible-sounding invention.

**Valid evidence sources, in order of strength:**

1. **Author's direct statement** in the current session. "I want the sequel to start five years later." Quote or confirm verbatim.
2. **Story export data** — queried via `extract_story_data` / `query_story_data`. What is actually written in turn outcomes, secret info, tracked item states, and story metadata.
3. **Original world JSON** — for values not addressed by the story export (carry-forward).

**Never acceptable as evidence sources:**

- The agent's own sense of what "probably" happened between story beats.
- Genre archetypes or sequel tropes ("sequels usually raise the stakes", "the hero's skills typically improve").
- Inferences from a character's name, appearance, or role.
- The agent's training data about narrative conventions.

---

## 2. If the export shows an empty or unchanged value, keep it empty or unchanged

Story exports often omit fields that didn't change during play. An empty Tracked Items section in a given turn doesn't mean items were lost — it means the export didn't include them for that turn. The right response is to carry forward the original world's value, not to invent a "likely" sequel state.

**Rule:** If the story export does not show a changed value for a field, default to the original world's value (`CARRY_FORWARD:`). Do not synthesize a new value to fill the gap.

This applies especially to:
- Tracked item labels and update instructions (the game may not have exercised them)
- NPC `detail` and `secret_info` (a character appearing in the story is not sufficient evidence to rewrite their dossier)
- Faction affiliations, relationship states, and arc resolutions not explicitly shown in the export

---

## 3. Don't invent story events

The story export is a record of what a real play session produced. Don't:
- Add events to a character's history that the export didn't show ("she must have left the guild by now")
- Resolve an ambiguity the story didn't resolve ("based on the export, they probably reconciled off-screen")
- Escalate stakes beyond what the export documented

If the export shows a cliffhanger or an unresolved arc, the sequel world inherits that ambiguity. An unresolved arc in `detail` should be flagged as unresolved — not papered over with a confident resolution.

---

## 4. If there's no story evidence for a field, say so explicitly

When you have checked the relevant extraction categories and found nothing that informs a field's value, use `NO_STORY_EVIDENCE:` in the Evidence line and describe what you looked for. This is not a failure — it is honest reporting that lets the author make a deliberate choice.

Do not substitute fabrication for a gap citation. A `NO_STORY_EVIDENCE:` line tells the author:
- What was checked (which turns, which categories)
- What was found (nothing, or nothing relevant)
- That the proposed value has no story grounding

The author can then supply the value via `USER_DIRECTED:`, choose to carry forward the original, or decide to leave the field blank.

---

## 5. Objective has no story-export source

There is no Objective section in IW story exports. The `objective` field must always be sourced from the original world (`CARRY_FORWARD:`) or from the author's explicit direction (`USER_DIRECTED:`). Never cite a turn or Story Metadata for the objective.

See [STORY_CONTEXT_DISTRIBUTION.md](./STORY_CONTEXT_DISTRIBUTION.md) for the full field-to-source mapping.

---

## 6. Characters: apply full character guardrails

All character fields (player characters and NPCs) carry the no-fabrication discipline from [CHARACTER_AUTHORING_GUARDRAILS.md](./CHARACTER_AUTHORING_GUARDRAILS.md). The story export is a valid source for character-level evidence, but only to the extent it explicitly shows character state — a character appearing in a turn outcome does not license rewriting their dossier.

Specific rules that interact with story exports:

- **`img_appearance` / `img_clothing` (NPCs) and `portraitPromptDetails` (player characters) have a source hierarchy in sequels.** The export won't contain ready-made image-generation *prompts*, but it usually *narrates* how characters look. So, in order: (1) **carry forward** from the source world if it already has them; (2) if not, **synthesize** them from how the story describes the character, citing the turn (`From Turn #N Outcome: …`) — re-expressing a narrated description as portrait-prompt text is grounding, not fabrication; (3) ask the author only when neither the source world nor the story provides anything. This is the sequel-specific extension of the general rule in [CHARACTER_AUTHORING_GUARDRAILS.md §2](./CHARACTER_AUTHORING_GUARDRAILS.md) (which is "author-input only" in new-world/modify/spinoff precisely because those flows have no story to draw on). What's still forbidden: inventing appearance the story never showed.
- **Character `detail` and `secret_info`:** The export may reveal new facts about a character (e.g., a secret revealed in `secretInfo`). These can update the sequel's NPC dossier — but only the explicitly revealed content, not inferred backstory.
- **Character mentions in the character index** confirm a character was referenced in the story, but not what happened to them. Use `query_story_data(category="turn_detail")` to get the actual context of any mention before making claims about a character's arc.

---

## 7. Query before proposing, not after

The correct workflow is:
1. Query the extraction data for the field being populated.
2. Review what the data shows.
3. Propose a value based on that data, with an Evidence line citing the relevant source.

The incorrect workflow is:
1. Draft a value based on intuition.
2. Search for evidence to justify it after the fact.

Evidence-first discipline catches fabrication before it reaches the author. Evidence-after-the-fact discipline rationalises it.

---

## Quick checklist

Before proposing any field value in a sequel-world session:

- [ ] Have I queried the relevant story data (not just assumed it doesn't exist)?
- [ ] Is the proposed value directly supported by the query result, the original world, or explicit author direction?
- [ ] Have I used `NO_STORY_EVIDENCE:` rather than invention when the query returned nothing relevant?
- [ ] Have I carried forward original world values with `CARRY_FORWARD:` rather than synthesising a sequel update?
- [ ] Have I avoided inferring character state, faction changes, or arc resolutions not shown in the export?

---

## Cross-references

- **Citation formats and the proposal template** → [CITATION_METHODOLOGY.md](./CITATION_METHODOLOGY.md)
- **Character no-fabrication** → [CHARACTER_AUTHORING_GUARDRAILS.md](./CHARACTER_AUTHORING_GUARDRAILS.md)
- **Which story data maps to which field** → [STORY_CONTEXT_DISTRIBUTION.md](./STORY_CONTEXT_DISTRIBUTION.md)
