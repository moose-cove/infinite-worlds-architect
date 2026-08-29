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

> **Deliberate plugin exception — `version` first in local drafts.** The `infinite-worlds-architect` tooling intentionally writes `version` as the *first* top-level key in the worlds it scaffolds and edits (`create_new_world_json` for new worlds, `make_draft_world` for `/modify-world` and `/spinoff-world` drafts), so an author sees the world's version the moment they open the raw file. This is the one place the plugin's local output diverges from the canonical order above, and it is a **local, pre-import** readability choice only: because IW renormalizes to the canonical order on import, `version` returns to its tail slot (`autoAdvanceVersion → version → designNotes`) in any imported or re-exported world. The lone cost is that diffing a plugin-authored draft against an IW export shows `version` relocated — expected and minor, since `version` is itself expected to differ across versions. Every other field still follows the canonical order, preserving the diff-stability benefit for the rest of the file.

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

## Import Is Lenient and Lossy — Never Strict

**The single most important thing to know about IW import.** Confirmed 2026-08-06 across two
probe round trips (`probes/probe-a-core.json`, `probes/probe-b-cap.json`): IW does not reject
a world it cannot fully understand. It **imports the world successfully and silently deletes
the parts it did not accept**, leaving everything around them intact.

Three distinct construct classes, across five probe cells, were destroyed this way — with no
error message in-game, in the editor, or in the export:

| Construct | What survived | What was deleted |
|---|---|---|
| Pre-v2.4 bare-array `triggerPrereqs`/`triggerBlockers` | trigger id, name, effects | the gate condition — trigger left with no conditions — and a trigger with no conditions never fires (confirmed in play 2026-08-22) |
| `triggerOnTrackedItem` with absent or empty `textComparison` | trigger id, name, effects | the entire condition |
| `initialTrackedItemValues` entry with `initialValueBasedOnPC: "player"` | the character, the tracked item | the per-character entry (entry-level: the incoming entry's own scope value drives the delete, whatever the item says — Probe E, 2026-08-28) |
| *(control)* each of those shapes done correctly | the construct under test, byte-identical | nothing |

**The likely single rule behind the first two.** Every destroyed *condition* — bare array where
an object was expected, object missing a required sub-key, object with an empty required
sub-key — produced a byte-for-byte identical outcome: the condition vanishes, the trigger's
`id`/`name`/`triggerEffects` survive, `triggerConditions` becomes `[]`. The generalisation
**"IW drops any trigger condition whose `data` payload it cannot parse, and never reports it"**
is better supported than three unrelated rules, and it predicts the same fate for malformed
condition shapes nobody has probed yet. Treat any condition `data` you are unsure of as
load-bearing. (The `initialTrackedItemValues` deletion is a separate mechanism — not a
condition.)

Two consequences worth internalising:

1. **A successful import proves nothing.** "It imported fine" is not evidence the world is
   intact. Only a re-export diff is.
2. **The damage erases its own evidence.** Because the offending construct is gone, a
   re-exported world validates *strictly more cleanly* than the file that went in:
   `probe-a-core.json` reports 4 errors / 4 warnings, `probe-a-imported.json` 0 errors /
   4 warnings at the time (7 since v0.21.0 began warning on the dead, conditionless triggers
   the deletion leaves behind) — while being semantically broken. Never treat a clean
   post-import validation as confirmation.

The practical rule: **validate before importing, not after.** `validate_world` is the only
place these constructs are still visible.

### Import is also *additive* — it does not only delete

"Lossy" is the headline, but deletion is not the only mutation. Two changes were made to
constructs that were not under test at all, both reproducible from the committed probe pairs:

- **A character with no `portraitPromptDetails` gains `portraitPromptDetails: {}`.** Probe B's
  character omitted the key entirely and came back carrying an empty object. (Probe A's
  character had it fully populated and it survived intact.) This is default injection, and it
  is the counter-example to reading "lenient and lossy" as "only ever removes".
- **The per-character `skills` *map* comes back reordered.** `{"Observation": 3, "Patience": 3}`
  → `{"Patience": 3, "Observation": 3}`, identically in both probes — consistent with it being
  deserialized into an unordered map server-side. Note the contrast: the **world-level**
  `skills` *array* held its order in both runs, as did every other array. **Never treat
  per-character skills-map ordering as meaningful**, and don't chase it as a finding when
  diffing a round trip.
- **A `"character"`-scoped tracked item with no per-character entry gets one auto-created**
  (`initialPCValue: ""`, scope `"character"`) — Probe E, 2026-08-28.
- **A surviving `initialTrackedItemValues` entry is exported with its `initialValueBasedOnPC`
  rewritten to its backing item's value** — entry-level scope is a projection, not stored
  state (Probe E). This is the one known case where **IW's own export is not re-importable
  losslessly**: an entry kept under a `"player"`-scoped item exports as player-scoped, which
  the next import deletes. An import → export → import → export cycle mutated the world on
  *both* imports (`probes/probe-e-imported.json` vs `probe-e-imported-2.json`).

Neither of the first two is harmful, and none affect validation — but all of them mean a
naive "is the export byte-identical to the source?" check will report a false positive on
any world, and the last one means even export→import is not guaranteed to be a fixed point.

---

## Other Import Findings

**Empty-field stripping is field-specific — do not generalize it.** `hideSkillSystem: false`
is stripped on import; only include it when `true` *(KB-sourced, not re-tested — neither probe
carried `hideSkillSystem`)*. But the broader claim this note used to
make — that IW strips any optional boolean set to its default — is **too broad**. In both
2026-08-06 probe round trips, `descriptionRequest`, `evaluationRequest`, `summaryRequest`,
`instructionBlocks`, `loreBookEntries` and `NPCs` were dropped when empty, while
`contentWarnings: ""`, `previewImage: ""`, `previewImageOptions: []`, `mature: false`,
`nsfw: false`, `favorite: false` and `autoAdvanceVersion: false` all survived untouched. The
stripping applies to a specific set of fields, not to a general "empty means absent" rule.

**A tracked item without a `description` key imports and plays but bricks the editor.**
Confirmed by bisection 2026-08-22 (Probe D build): a world whose tracked items had every
required field but no `description` imported with the normal "World imported from raw JSON"
message and could be played, yet clicking **Edit** on it did nothing — no dialog, no error,
the world list just stayed put. Adding `"description"` (even an empty string) to each item
fixed it; removing it reproduced it. The editor is the only route to the raw-JSON import box,
so such a world cannot be repaired in the app — fix the file first. `validate_world` errors on
the missing key (v0.21.0). The JSON Schema still lists `description` as optional because the
platform's own exports always write it.

**Raw-JSON import persists immediately.** In the editor, **Import JSON to world** asks "Are you
sure you wish to overwrite…", then reports "World imported from raw JSON." — and the world is
already saved at that point: **Save changes and exit** afterwards says "No changes to save."
**Discard changes** does not undo an import. On a large world the import alert can arrive
10–20 s after the click. (Observed via the Playwright harness in `probes/harness/`.)

**An absent `triggerConditions` key is normalized to `[]` at import — and is equally dead.**
Probe E (2026-08-28): a trigger authored with no `triggerConditions` key at all exported with
`"triggerConditions": []`, and in play sat at "not yet fired" for three turns while an
always-true control fired every turn. Absent and empty are the same runtime-dead state; the
Start-of-Game flag remains the only conditionless trigger that fires.

**`recommendedAIModel` is not validated.** Probe E imported `"notarealmodel"` and it survived
two round trips verbatim. The field is stored as free text: IW neither rejects nor normalizes
unknown values, so there is no enforced enum to discover. Author real model strings anyway
(`"smilodon"`, `"lynx"`, …) — the platform will happily preserve a typo.

**`autoAdvanceVersion: false` holds `version` still across a round trip.** Useful when
diffing an import: it removes the version-drift noise described below.

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

> **Status of `hidden_boring` / `ai_only_boring` as `visibility` values — split as of 2026-08-06.** These are newly-added `visibility` enum values (added to the schema's `visibility` enum).
>
> - **`hidden_boring` — CONFIRMED.** Probe A (`probes/probe-a-core.json`, item `PrbHidBor`) round-tripped it through an IW import byte-identical. It survives import and is safe to author.
> - **`ai_only_boring` — still `[PENDING TEST]`.** Neither probe exercised it. Authorable, but round-trip survival is assumed from its sibling rather than observed.
>
> Read-visibility semantics for both remain KB-sourced and untested at runtime: `hidden_boring` is **AI-cannot-read** — the storyteller AI cannot see its value (same read-visibility as `hidden`); the `_boring` modifier additionally hides it from the standard "Hidden tracked items" view unless "Extra-hidden" is checked. Import survival is what the probe settled; what the AI can actually read is not.

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

Shows which triggers fired or were evaluated each turn. Useful for confirming trigger chains, prereqs, and blockers behaved as expected. In the in-game **World debug tools** modal (bug icon on the play toolbar) it appears as a collapsible **Triggers (N)** section — "Triggers fired this turn" plus "All triggers" with per-trigger status ("fired turn 1", "first fired turn 1, last turn 4, fired 4 times", "not yet fired"). A trigger whose condition or script errored is flagged inline ("1 problem, see PawScript below").

### PawScript panel and Expression Sandbox

The same modal has a **PawScript (N)** section (enable "PawScript (scripts…)" in the World debug tools checkboxes) listing, per trigger, whether its condition fired and whether its script ran, with the exact failure text when something broke — `Field 'ghost' not found`, `Cannot apply '*' to text and a number`, "A script stopped early, on line 1", "Its condition couldn't be worked out, so the trigger didn't run". These messages are how the 2026-08-22 runtime findings were read; when a trigger "should have fired", look here before changing anything.

Every entry has an **Open in Sandbox** link to the **PawScript Expression Sandbox**: a CodeMirror editor with an **Evaluate** button that runs any expression against the *real* data of that turn and reports the result — 🟢 "TRUE — the trigger would fire", 🔴 FALSE, ⚠️ "This works out to '100', not true or false — so the trigger never fires", or the error text. It costs no credits, so it is the cheapest way to test a condition before spending a turn on it.

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
