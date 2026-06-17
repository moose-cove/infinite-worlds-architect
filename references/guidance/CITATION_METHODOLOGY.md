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

### Format 4 — GAP FOUND

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

## 4. Multiple Proposals in One Message

When proposing several fields in one message, each proposal block is checked independently. All must be well-formed:

```
**Field:** title
**Proposed Value:** The Iron Throne — Second Age
**Evidence:** From Story Metadata

**Field:** objective
**Proposed Value:** Reclaim the kingdom
**Evidence:** CARRY_FORWARD: Same overarching goal carried from the source world; story export shows ongoing struggle.

**Field:** background
**Proposed Value:** A generation has passed since the war…
**Evidence:** From Turn #1 Outcome: The narrator described a twenty-year interval since the events of the first game.
```

If any single block lacks a well-formed evidence line, the gate blocks the entire response and names the offending field(s).

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
- **Querying extracted data** → [mechanics/STORY_EXTRACTION_TOOL.md](../mechanics/STORY_EXTRACTION_TOOL.md)
- **Character authoring discipline** → [CHARACTER_AUTHORING_GUARDRAILS.md](./CHARACTER_AUTHORING_GUARDRAILS.md)
