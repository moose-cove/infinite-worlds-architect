# Platform Behavior Notes

> **Provenance:** KB-empirical — confirmed via import testing and community observation (KB v2.8, May 2026). This is platform state, not schema-governed. Behaviors may change as IW is updated; the schema and fixture remain the authoring source of truth.

---

## Canonical JSON Field Ordering

IW reorders JSON fields to its internal canonical order on import. Generating worlds in this order makes diff comparisons easier and avoids spurious changes when re-exporting.

**Top-level canonical order:**

```
favorite → title → description → background → instructions → authorStyle
→ recommendedAIModel → firstInput → objective → imageModel → imageStyle
→ [illustration style fields] → [imageStyle pre/post fields]
→ mature → nsfw → contentWarnings → enableAISpecificInstructionBlocks
→ previewImage → fullSizePreviewImage → previewImageOptions
→ fullSizePreviewImageOptions → currentPreviewImageIndex → imagePromptDetails
→ permissionsOnceShared → [allowChange* fields]
→ descriptionRequest → evaluationRequest → hideSkillSystem → summaryRequest
→ schemaVersion → charSelectText → skills
→ possibleCharacters → triggerEvents → victoryCondition → defeatCondition
→ instructionBlocks → loreBookEntries → trackedItems → NPCs
→ autoAdvanceVersion → version → designNotes
```

Note: `schemaVersion` is near the **end** of the canonical ordering (position ~40), not the beginning. `hideSkillSystem` sits between `evaluationRequest` and `summaryRequest` in the fixture, but is stripped on import when `false` (see [Other Import Findings](#other-import-findings)) — so it only appears in this slot when set to `true`.

> **Deliberate plugin exception — `version` first in local drafts.** The `infinite-worlds-architect` tooling intentionally writes `version` as the *first* top-level key in the worlds it scaffolds and edits (`create_new_world_json` and the `/modify-world` + `/spinoff-world` flows), so an author sees the world's version the moment they open the raw file. This is the one place the plugin's local output diverges from the canonical order above, and it is a **local, pre-import** readability choice only: because IW renormalizes to the canonical order on import, `version` returns to its tail slot (`autoAdvanceVersion → version → designNotes`) in any imported or re-exported world. The lone cost is that diffing a plugin-authored draft against an IW export shows `version` relocated — expected and minor, since `version` is itself expected to differ across versions. Every other field still follows the canonical order, preserving the diff-stability benefit for the rest of the file.

**Canonical sub-object ordering:**

| Object | Canonical order |
|---|---|
| Trigger | `id → name → advancedLogic → triggerEffects → triggerConditions → triggerOnStartOfGame → canTriggerMoreThanOnce` |
| Effect | `id → data → type` |
| Condition (number type) | `category → type → data → id → trackedItemID → inequality` |
| Condition (text/xml type) | `category → type → data → id → trackedItemID` |
| `imagePromptDetails` inner fields | `illustrGenre → illustrClothes → illustrSetting → illustrSubject → illustrAppearance → illustrIsCharacter → illustrExpressionPosition` |

---

## Silent ID-Rename Hazard

**KB-empirical — June 2026 import test.** IW silently renames **tracked-item** (`trackedItems[].id`) IDs that contain non-alphanumeric characters to random 9-char alphanumeric strings on import, WITHOUT updating trigger references. The same test observed instruction-block, lore-book-entry, and trigger-event IDs with `+`/`/` survive import unchanged.

**Empirical evidence from the June 2026 import test:**
- `trkPlus+1` (tracked item, contains `+`) → silently renamed to `JOgXHlGyO`
- `trkSlsh/2` (tracked item, contains `/`) → silently renamed to `Yi3bE076Q`
- `trkClean3` (tracked item, alphanumeric control) → unchanged
- `eibPlus+6` (instruction block, contains `+`) → **unchanged** (survived import)
- `kibSlsh/7` (lore book entry, contains `/`) → **unchanged** (survived import)
- `Trg+Spc4` (trigger event, contains `+`) → **unchanged** (survived import)

After the rename, IW did **not** remap references: the 8 trigger conditions and effects pointing at `trkPlus+1` / `trkSlsh/2` (via `trackedItemID` on both `triggerOnTrackedItem` conditions and `effectSetTrackedItemValue` effects) were left pointing at the now-dead IDs, producing silent dead triggers.

**IDs at risk:** `trackedItems[].id` values containing any non-alphanumeric character (`+`, `/`, `-`, `_`, spaces, etc.). The observed renames involved `+` and `/`; the broader pattern (any non-alnum char) is the safer rule to follow.

**As of v0.10.0, `mint_ids` emits alphanumeric-only IDs (`A-Za-z0-9`) for all entity kinds**, eliminating this hazard for machine-minted IDs. The `validate_world` tool now warns when a tracked-item ID contains non-alphanumeric characters.

**Why this is dangerous:** All trigger references to the renamed tracked-item ID break silently. The trigger appears valid in the world editor but never fires because it references an ID that no longer exists.

### Global String-Replace Remap Procedure

When you need to rename a tracked item, instruction block, or lore book entry ID, do a **global string replace across the entire raw JSON** — not just the entity's own `id` field.

IDs appear in string content as well as structured fields. For tracked items, check and update all of:

- `trackedItems[].id` (the entity definition)
- `triggerOnTrackedItem` conditions: `data.trackedItemID` AND top-level `trackedItemID`
- `effectSetTrackedItemValue`: `data.trackedItemID` AND top-level `trackedItemID`
- `effectModifyTrackedItemDetails`: `data.trackedItemID` AND top-level `trackedItemID`
- `effectPresentChoice`: `data.targetTrackedItemId`
- `effectRequestInput`: `data.targetTrackedItemId`
- Any `<<old_id_name>>` variable references in `instructions`, `updateInstructions`, EIB content, KIB content, `descriptionRequest`, `evaluationRequest`, `summaryRequest`, `background`, and narrative text fields

For instruction block IDs (`instructionBlocks[].id`), check:
- `effectModifyInstructionBlock`: `data.id`

For lore book entry IDs (`loreBookEntries[].id`), check:
- `effectModifyKeywordBlock`: `data.id`

**Recommended approach:** Use a text editor's "Find All" + "Replace All" across the raw JSON string. Do not rely on structured field navigation alone.

---

## Other Import Findings

**`hideSkillSystem: false` stripped on import.** IW strips optional boolean fields when set to their default (`false`) value. Do not rely on its presence in exported JSON. Only include it when `true`.

**`version` auto-increments per save, not per import.** A world imported as `v3.00` and then edited twice will show `v3.02`. The `version` field counts any save event when `autoAdvanceVersion: true` — not just the first import. Do not use `version` to count imports.

**Post-UI-browse JSON = post-import JSON.** Browsing and opening fields in the UI editor does not cause further structural changes after the initial import. The orphan-cleanup behavior (stripping invalid data when fields are opened) did not trigger in testing.

**`selectedAIProfiles` requires explicit thinking variants.** `smilodon` and `smilodon-thinking` are distinct model strings. An EIB using `selectedAIProfiles: ["smilodon"]` does NOT apply when the player uses `smilodon-thinking`. List every applicable model string explicitly.

---

## World Debug Tools

Accessible via the Storyteller option menu (Storyteller must be enabled first). Opens as **"World debug tools"** with the subtitle "Here be dragons" and a warning that these tools are for world designers, not regular players.

**Four checkboxes — select any combination:**

| Checkbox | What it shows |
|---|---|
| Instructions sent to the AI | **Active Instructions** panel — full text of MI, all EIBs, any KIB matched this turn |
| Trigger event status | Which triggers fired or were evaluated this turn |
| AI thinking and evaluation | AI's chain-of-thought (thinking models only) and evaluation output |
| Include "Extra-hidden" tracked items in "Hidden tracked items" view | Reveals `ai_only_boring` and `hidden_boring` TIs in the tracked items view |

> **"Extra-hidden"** is IW's official term for the boring modifier (`ai_only_boring` / `hidden_boring`). The `_boring` suffix in the JSON maps to the "Extra-hidden" UI concept.

> **Status of `hidden_boring` / `ai_only_boring` as `visibility` values — KB-empirical, `[PENDING TEST]`.** These are newly-added `visibility` enum values (added to the schema's `visibility` enum) and have **not** yet been confirmed by an import round-trip test. `hidden_boring` is **AI-cannot-read** — the storyteller AI cannot see its value (same read-visibility as `hidden`); the `_boring` modifier additionally hides it from the standard "Hidden tracked items" view unless "Extra-hidden" is checked. Treat these as authorable-but-import-test-pending rather than settled values until a fixture confirms round-trip survival.

### Active Instructions Panel

Shows the **full text content** of every currently active instruction source:
- Main Instructions (MI) — always present; always active
- All EIBs — always active (profile gating determines whether a given AI *applies* the EIB, but it always shows here)
- Any KIB whose keyword was matched this turn

**Critical for trigger-based worlds:** Changes made by triggers (`effectModifyInstructionBlock`, `effectChangeMainInstructions`, `effectModifyKeywordBlock`) are **not** reflected in the world edit screen. The **only** way to see live post-trigger instruction state is this panel.

**Reference resolution check:** If an EIB, MI, or activated KIB contains `<<tracked_item_name>>` references, this panel shows either the resolved value or the literal `<<>>` tag — a reliable way to confirm reference resolution is working.

### Inactive Instructions Panel

A separate panel (not a checkbox). Shows **names and keyword triggers** of all KIBs whose keywords were **not** matched this turn. Does not show KIB contents. Useful for confirming KIB keyword state after disable/re-enable triggers.

Only KIBs can be inactive. EIBs and MI are always active and never appear here.

### Trigger Event Status

Shows which triggers fired or were evaluated each turn. Useful for confirming trigger chains, prereqs, and blockers behaved as expected.

### AI Thinking and Evaluation

Shows the AI's chain-of-thought (thinking models only) and evaluation output. Specialist instructions (`evaluationRequest`, `descriptionRequest`, `summaryRequest`) do not appear in Active Instructions but their effect may be partially visible here.

---

## IW Export Function

IW can package a played game's content for download. Primarily a player convenience feature, but also valuable for testing, debugging, and sharing results with an AI assistant for analysis.

### What the Export Includes (Selectable)

| Option | Content |
|---|---|
| **Turns** | Up to 100 turns; specify by number or range (e.g. `1, 3-5, 8`). Always includes the outcome description for each turn. |
| **Background** | The world's background text (the zero-turn scene-setting). Acts as a cover page in PDF. |
| **Character** | The active player character's details. |
| **Secret info** | The AI-generated `secretInfo` entry for each selected turn. |
| **Tracked items** | Value of all player-visible tracked items at each selected turn. |
| **Hidden tracked items** | Value of `hidden`/`ai_only` tracked items at each turn. Only available in Storyteller Mode. |

### Output Formats

| Format | Best for |
|---|---|
| **Text file** | AI analysis, maximum information density, smallest file size |
| **PDF** | Human reading, sharing, printing |
| **PDF page images** | Images of each PDF page (rarely needed) |
| **Illustrations** | Generated images for each turn as a folder |

**Use text file format for sharing with Claude.** It includes all selected data in a compact, parseable format without PDF overhead.

### What the Export Does NOT Include

- World Debug items (Active Instructions, Inactive Instructions, Thinking, Evaluation) — debug views only
- The world JSON itself — export that from the world edit screen, not the play export
- Post-trigger-modified instruction text — the export reflects player-accessible content only

> **Note on "extra-hidden" items in exports:** `hidden_boring` and `ai_only_boring` items likely do not appear in the export's "Hidden tracked items" section even in Storyteller Mode — they may be below the visibility floor of the export. Confirm during testing.

### Testing Use Pattern

When running test sessions, export with all options enabled (Background + Character + Secret info + Tracked items + Hidden tracked items + all turns) as a text file. Share the text file in the next conversation for AI analysis. An AI assistant can cross-reference:
- TI values at each turn (confirms trigger-set values, reference-updated values)
- `secretInfo` entries (confirms AI's internal state tracking)
- Turn outcomes (confirms description/author style changes, knowledge isolation)
