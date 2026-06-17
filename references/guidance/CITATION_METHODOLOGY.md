# Citation Methodology

This document governs how the agent **cites evidence** when proposing world-field values during a `sequel-world` flow. The citation gate Stop hook enforces this protocol automatically; every violation blocks the response until a well-formed evidence line is added.

Read this before beginning any field proposal in a sequel-world session.

---

## 1. The Mandated Proposal Template

Every field proposal in a sequel-world session MUST use this exact block structure:

```
**Field:** <field name>
**Proposed Value:** <value>
**Evidence:** <evidence in one of the 4 accepted formats below>
```

All three lines are required. The `**Evidence:**` line should appear within the same proposal block — before the next `**Field:**` heading. The gate does not enforce strict line-adjacency between `**Proposed Value:**` and `**Evidence:**`, but it does require both `**Field:**` and `**Proposed Value:**` to be present with no blank line between them (a blank line there breaks the structural match and causes the gate to treat the proposal as unverifiable). Only the `**Evidence:**` line is inspected for content; `**Field:**` and `**Proposed Value:**` are structural anchors.

**Propose one field per message by default.** A single field, one block, then wait for approval. The exception is complex entities with several sub-fields — NPCs, tracked items, trigger events, and instruction blocks — which are proposed in small ordered batches of blocks; see [§4](#4-how-many-fields-per-message--and-complex-field-batching).

> **Evidence is shown in chat prose only.** It is never written to the world JSON. The JSON file receives the value, not the citation.

---

## 2. The Four Accepted Evidence Formats

### Format 1 — STORY CITATION

Use when the value is directly supported by story-export data.

**Accepted forms:**

```
From Turn #<N> Outcome: <brief quote or paraphrase>
From Turn #<N> Secret Info: <brief quote or paraphrase>
From Turn #<N> Tracked Item <item name>: <value or paraphrase>
From Story Metadata
```

`From Story Metadata` applies when the value comes from `metadata.json` fields (title, story background, character name/skills/background).

> The gate validates the **prefix** only — `From Turn #<N>` or `From Story Metadata`. The `Outcome:` / `Secret Info:` / `Tracked Item <name>:` suffix is a readability convention (tell the author *where* in the turn the evidence is), not something the hook enforces. Use it anyway — it's what makes a citation auditable.

**Examples:**

```
**Evidence:** From Turn #12 Outcome: The party arrived at the fortress gates.
**Evidence:** From Turn #5 Secret Info: Mira revealed she was working for the council.
**Evidence:** From Turn #7 Tracked Item Health: 75
**Evidence:** From Story Metadata
```

The turn number must be a real turn from the extraction (verified via `turn_index`). Do not cite a turn that hasn't been queried.

---

### Format 2 — USER DIRECTED

Use when the author has explicitly instructed you to use a specific value, regardless of what the story export shows.

**Form:**

```
USER_DIRECTED: <brief description of what the author said>
```

**Example:**

```
**Evidence:** USER_DIRECTED: Author said to set the protagonist's name to "Kira" for the sequel.
```

Do not use this format speculatively — only when the author has given a direct instruction during this session.

---

### Format 3 — CARRY FORWARD

Use when the value is unchanged from the original world and no story event contradicts it.

**Form:**

```
CARRY_FORWARD: <brief explanation of why it carries forward unchanged>
```

**Example:**

```
**Evidence:** CARRY_FORWARD: Same world title as source world; no story events changed it.
**Evidence:** CARRY_FORWARD: NPC Daro's faction affiliation was not addressed in the story export.
```

> **The `objective` field always requires this format** (or `USER_DIRECTED:`). There is no Objective section in IW story exports, so story citations are never available for `objective`. See [STORY_CONTEXT_DISTRIBUTION.md](./STORY_CONTEXT_DISTRIBUTION.md).

---

### Format 4 — NO STORY EVIDENCE

Use when you have checked the story export and found no evidence for a field, and you are not carrying a value forward from the source world.

**Form:**

```
NO_STORY_EVIDENCE: <brief description of what you looked for and didn't find>
```

**Example:**

```
**Evidence:** NO_STORY_EVIDENCE: No background description found in story metadata or any queried turn. Using author-supplied value.
```

Prefer an explicit gap citation over silence. A `NO_STORY_EVIDENCE:` citation tells the author exactly what was checked and what was missing — it is honest and auditable, and more useful than an unexplained carry-forward.

---

## 3. Invalid Evidence Lines (gate will block these)

The following are common malformed evidence lines the gate rejects:

| Bad line | Why it's rejected |
|---|---|
| `**Evidence:** I inferred this from the genre.` | Does not match any prefix |
| `**Evidence:** Based on story context` | Missing required prefix |
| `**Evidence:** From the story` | Missing `Turn #<N>` or `Story Metadata` form |
| `**Evidence:** USER_DIRECTED:` (no text after colon) | Prefix present but body is empty |
| `**Evidence:** CARRY_FORWARD:` (no text after colon) | Prefix present but body is empty |
| `**Evidence:** NO_STORY_EVIDENCE:` (no text after colon) | Prefix present but body is empty |

Empty-body citations are rejected. Each prefix must be followed by at least one non-whitespace character.

---

## 4. How many fields per message — and complex-field batching

**Default: one field per message.** Propose a single field, wait for the author to approve or revise, then move to the next. One block per message keeps each evidence line easy to audit and each approval unambiguous.

**The exception: complex entities with several sub-fields.** Some world objects — NPCs, tracked items, trigger events, and instruction blocks — are built from related sub-fields that only make sense together; proposing them one-per-message would hide the shape of the whole entity. Propose them in the small, ordered batches below. Each batch is still **one message containing several proposal blocks**, and the gate checks every block independently — so every sub-field in the batch needs its own well-formed `**Evidence:**` line. **Approve each batch before proposing the next**, so the author can course-correct early.

Field names below are the schema's (`world_v2.1.schema.json`). The IW editor's author-facing labels differ slightly (e.g. "Brief Summary" = `one_liner`, "Full List of Names" = `names`) — use whichever naming is clearest to the author, but make sure each value lands in the right JSON field.

### Tracked item (`trackedItems[*]`)
1. `name`, `dataType` (storage type), `visibility` (who can see it).
2. `description`, `autoUpdate` (whether the AI updates it each turn), `updateInstructions` (only meaningful when `autoUpdate` is true).
3. Any remaining relevant fields (`initialValue`, `initialValueBasedOnPC`).

> Schema-required tracked-item fields are `name`, `dataType`, `visibility`, **and `autoUpdate`** — every tracked item must end up with all four, or `validate_world` will reject it. Don't let `autoUpdate` slip through batch 2 unset.

### Keyword Instruction Block (`loreBookEntries[*]`)
1. `name`, `keywords` (the activating terms), and `content` — in one message.

### Extra Instruction Block (`instructionBlocks[*]`)
1. `name` and `content` — in one message.

### NPC (`NPCs[*]`)
1. `name`, `names` (full list of alternative names / aliases), `location`, `one_liner` (brief summary).
2. `detail` (character detail) and `secret_info`.
3. `appearance` (narrative physical description) and the portrait prompts `img_appearance` / `img_clothing`.

### Trigger event (`triggerEvents[*]`)
1. `name` and the `triggerConditions` (when it fires). `triggerConditions` may be empty for a start-of-game / always-fire trigger (`triggerOnStartOfGame`); only `triggerEffects` is schema-required.
2. The `triggerEffects` (what it does).

**Worked example — a single NPC batch-1 message:**

```
**Field:** NPC "Mira" — name
**Proposed Value:** Mira
**Evidence:** CARRY_FORWARD: Same NPC as the source world.

**Field:** NPC "Mira" — names (aliases)
**Proposed Value:** ["Mira", "the Courier"]
**Evidence:** From Turn #8 Outcome: A guard addressed her as "the Courier".

**Field:** NPC "Mira" — location
**Proposed Value:** The river docks
**Evidence:** From Turn #14 Outcome: Mira was last seen leaving the river docks.

**Field:** NPC "Mira" — one_liner
**Proposed Value:** A courier who now runs the dock smugglers.
**Evidence:** From Turn #14 Secret Info: Mira had taken over the smuggling ring.
```

If any single block in a batch lacks a well-formed evidence line, the gate blocks the whole message and names the offending sub-field(s).

---

## 5. Good vs. Bad Examples (Summary)

**GOOD — all four formats:**

```
**Evidence:** From Turn #3 Outcome: The city was destroyed in the final battle.
**Evidence:** From Story Metadata
**Evidence:** USER_DIRECTED: Author explicitly asked for a darker tone in the sequel.
**Evidence:** CARRY_FORWARD: The protagonist's skill set was unchanged by the story events.
**Evidence:** NO_STORY_EVIDENCE: No mention of image style in any export section; using author default.
```

**BAD — all rejected:**

```
**Evidence:** This seems like a reasonable sequel premise.
**Evidence:** Based on typical fantasy conventions.
**Evidence:** From the story.
**Evidence:** USER_DIRECTED:
**Evidence:** CARRY_FORWARD:
```

---

## Cross-references

- **No-fabrication discipline for sequels** → [STORY_ACCURACY_GUARDRAILS.md](./STORY_ACCURACY_GUARDRAILS.md)
- **Which fields map to which story data** → [STORY_CONTEXT_DISTRIBUTION.md](./STORY_CONTEXT_DISTRIBUTION.md)
- **Character authoring discipline** → [CHARACTER_AUTHORING_GUARDRAILS.md](./CHARACTER_AUTHORING_GUARDRAILS.md)
