
# Schema reference (derived from `test-files/example-world-schema-v2.1.json`)

This is the canonical schema for the v2.1 Infinite Worlds world JSON, derived from `example-world-schema-v2.1.json`. Where the fixture is silent on a field's exact semantics, that uncertainty is noted inline; the plugin's validator should warn (not error) on such fields and preserve their values verbatim on round-trip.

**Convention**: in the tables below, "Editable" means an author edits this directly. "Platform-managed" means the platform writes it (image URLs after image generation, IDs after entity creation, runtime state). "Hybrid" means the author provides input data but the platform may modify it.

## Table of Contents

- [1 Top-level fields](#1-top-level-fields)
- [2 `possibleCharacters[*]` (player characters)](#2-possiblecharacters-player-characters)
- [3 `NPCs[*]`](#3-npcs)
- [4 `trackedItems[*]`](#4-trackeditems)
- [5 `triggerEvents[*]`](#5-triggerevents)
  - [`triggerConditions[*]`](#triggerconditions)
  - [`triggerEffects[*]` — canonical list from v2.1 fixture](#triggereffects--canonical-list-from-v21-fixture)
- [6 Instruction blocks](#6-instruction-blocks)
- [7 Player permissions](#7-player-permissions)
- [8 Image prompt details (world + per-character)](#8-image-prompt-details-world--per-character)
- [9 Template variable system](#9-template-variable-system)

---

## 1 Top-level fields

| Key | Type | Category | Notes |
|---|---|---|---|
| `schemaVersion` | number | Platform | `2.1` in current fixture. Read on input, write on output. Warn on unknown versions. |
| `title` | string | Editable | World name |
| `description` | string | Editable | User-facing blurb shown in the world browser |
| `background` | string | Editable | Initial story situation sent to the AI |
| `instructions` | string | Editable | Main authoring instructions for the AI |
| `authorStyle` | string | Editable | Writing style (free-form, e.g., "Diana Wynne Jones cozy fantasy") |
| `firstInput` | string | Editable | Hidden turn-0 prompt — what the player's character "does" before the story starts |
| `objective` | string | Editable | Player's primary goal |
| `mature` | boolean | Editable | R-rated content flag. `true` indicates the world contains mature themes (violence, suggestive content, etc.) but not necessarily explicit sexual content. If `nsfw` is `true`, `mature` must also be `true` — `nsfw` implies `mature`. |
| `nsfw` | boolean | Editable | X-rated content flag. `true` indicates explicit sexual content. Implies `mature: true` — a world cannot be `nsfw` without also being `mature`. |
| `contentWarnings` | string | Editable | Comma-separated themes; free-form |
| `descriptionRequest` | string | Editable | Custom override of the per-turn description instruction. The fixture's value is the platform's own UI explanation of this field — read it for semantics. |
| `evaluationRequest` | string | Editable | Custom override of the per-action evaluation instruction (skill checks etc.). The fixture's value documents the template variables: `<<skill_list>>`, `<<difficulty_list>>`, `<<skill_example>>`, `<<difficulty_example>>`, `<<skills_and_levels>>` |
| `summaryRequest` | string | Editable | Custom override of the summarisation instruction. The fixture's value explains the field. |
| `hideSkillSystem` | boolean | Editable | Hides skills from character chooser/customiser/sheet. Paired with `evaluationRequest` overrides — if the author replaces the evaluation system, they may want to hide the default skill UI. |
| `imageModel` | string | Editable | E.g., `"manticore"`, `"flux.1-schnell"` |
| `imageStyle` | string | Editable | E.g., `"photo_1"`, `"photo_beautiful"` |
| `imageStyleCharacterPre` | string | Editable | Prefix for character image prompts |
| `imageStyleCharacterPost` | string | Editable | Suffix for character image prompts (often contains LoRA names like `IWUpscaleFace`) |
| `imageStyleNonCharacterPre` | string | Editable | Prefix for setting image prompts |
| `imageStyleNonCharacterPost` | string | Editable | Suffix for setting image prompts |
| `illustrationStyleCharacterLowPriority` | string | Editable | Newer character image style field (coexists with `imageStyleCharacter*`). Exact precedence rules versus the older fields are unverified — preserve all values and treat both sets as author-editable. |
| `illustrationStyleCharacterHighPriority` | string | Editable | Newer character image style field (see `illustrationStyleCharacterLowPriority` row) |
| `illustrationStyleNonCharacterLowPriority` | string | Editable | Newer non-character image style field |
| `illustrationStyleNonCharacterHighPriority` | string | Editable | Newer non-character image style field |
| `enableAISpecificInstructionBlocks` | boolean | Editable | When true, Extra Instruction Blocks gain a `selectedAIProfiles` field restricting them to specific AI models |
| `recommendedAIModel` | string \| null | Editable | E.g., the platform may have profiles like `"smilodon"`; `null` when no recommendation. The full enum of valid values is unverified — preserve any value the fixture provides. |
| `victoryCondition` | object | Editable + Platform | `{condition: string, text: string, alreadyFired: boolean}`. `alreadyFired` is platform runtime state — never write `true` from the plugin. `condition` is a free-form English expression the platform evaluates. `text` is the message shown on victory. May be `null` if not configured. |
| `defeatCondition` | object | Editable + Platform | Same shape as `victoryCondition`. Default `text` if not overridden: `"Your adventure ends here. Game over."` |
| `designNotes` | string | Editable | Author's notes — NOT sent to the AI. For author reference only. The fixture uses it to record the original world-design prompt. |
| `charSelectText` | string | Editable | Optional text shown on the character selection screen |
| `skills` | string[] | Editable | List of world-level skill names (e.g., `["Baking", "Creativity", ...]`). Each becomes a template variable `skill_<lowercased>` |
| `possibleCharacters` | object[] | Editable + Platform | Player characters — see §2 |
| `NPCs` | object[] | Editable | Non-player characters — see §3 |
| `trackedItems` | object[] | Editable | World state variables — see §4 |
| `triggerEvents` | object[] | Editable + Platform | Conditional events — see §5 |
| `instructionBlocks` | object[] | Editable | "Extra Instruction Blocks" — non-keyword always-active instructions. See §6 |
| `loreBookEntries` | object[] | Editable | "Keyword Instruction Blocks" — keyword-triggered instructions. See §6 |
| `allowChangeCharacterName` | boolean | Editable | Player permissions — see §7 |
| `allowChangeCharacterDescription` | boolean | Editable | (same) |
| `allowChangeCharacterSkills` | boolean | Editable | (same) |
| `allowChangeCharacterItemValues` | boolean | Editable | (same) |
| `allowChangeCharacterPortrait` | boolean | Editable | (same) |
| `allowChangeCharacterNewPortrait` | boolean | Editable | (same) |
| `imagePromptDetails` | object | Hybrid | World preview image prompt details — see §8 |
| `previewImage` | string (URL) | Platform | World preview image URL — generated by the platform |
| `fullSizePreviewImage` | string (URL) | Platform | Full-size variant |
| `previewImageOptions` | string[] | Platform | Alternative URLs the platform generated for the same prompt |
| `fullSizePreviewImageOptions` | string[] | Platform | (same) |
| `currentPreviewImageIndex` | number | Platform | Which option is selected |
| `permissionsOnceShared` | object | Editable | `{sharing: boolean, editing: boolean}`, both default `true`. `sharing: true` permits other players to share the world more widely (e.g., re-share into their own collections). `editing: true` permits other players to edit the world to create their own variants. Cross-field invariant: `editing: true` implies `sharing: true` (the platform UI auto-checks `sharing` when `editing` is enabled). |
| `favorite` | boolean | Platform | UI state (user starred this world) |
| `version` | string | Platform | E.g., `"1.02"` — author's content version, bumped by the platform |
| `autoAdvanceVersion` | boolean | Editable | Whether the platform auto-bumps version on edits |

## 2 `possibleCharacters[*]` (player characters)

| Key | Type | Category | Notes |
|---|---|---|---|
| `name` | string | Editable | Character name |
| `description` | string | Editable | Character description, shown on the character chooser |
| `skills` | object | Editable | `{[skillName]: number}` — keys must match world-level `skills` array. Values are integers (likely 0–5 by convention; verify against more fixtures) |
| `characterId` | string | Platform | 8-character ID; assigned on creation. Referenced from `triggerOnCharacter` conditions. |
| `portrait` | string (URL) | Platform | Currently-selected portrait |
| `fullSizePortrait` | string (URL) | Platform | (same) |
| `portraitOptions` | string[] | Platform | Generated alternatives |
| `fullSizePortraitOptions` | string[] | Platform | (same) |
| `currentPortraitIndex` | number | Platform | (same) |
| `portraitPromptDetails` | object | Hybrid | Author-provided prompt info used to generate the portrait. Same shape as world-level `imagePromptDetails` — see §8 |
| `initialTrackedItemValues` | object[] | Editable | Per-character starting values for tracked items. Each entry: `{id: string, name: string, visibility: string, initialPCValue: string \| string[], initialValueBasedOnPC: string}`. The `id` references a tracked item by its ID. `initialPCValue` may be a string OR a string array — see §4 for the array semantics. |

## 3 `NPCs[*]`

| Key | Type | Category | Notes |
|---|---|---|---|
| `id` | string | Platform | Unique ID |
| `positionInList` | number | Editable | 0-based display order |
| `name` | string | Editable | NPC display name |
| `detail` | string | Editable | Long character detail — the "Character Detail" field in the platform UI |
| `one_liner` | string | Editable | Short summary — the "Brief Summary" field in the platform UI |
| `appearance` | string | Editable | Free-form appearance description |
| `location` | string | Editable | Where this NPC is encountered |
| `secret_info` | string | Editable | Info available to the AI but not the player |
| `names` | string[] | Editable | All names/aliases the character is known by |
| `img_appearance` | string | Editable | Image-generation appearance text (visual-only) |
| `img_clothing` | string | Editable | Image-generation clothing text |

## 4 `trackedItems[*]`

| Key | Type | Category | Notes |
|---|---|---|---|
| `id` | string | Platform | Unique ID |
| `name` | string | Editable | Display name. Becomes a template variable `<<name_in_snake_case>>` |
| `positionInList` | number | Editable | 0-based display order |
| `dataType` | string | Editable | One of: `"text"`, `"number"`, `"xml"`. (XML items use embedded XML for structured state — see the fixture's "Secret Grudges" example) |
| `visibility` | string | Editable | One of: `"everyone"`, `"ai_only"`, `"ai_only_boring"`, `"player_only"`, `"hidden"`. `"ai_only"` and `"ai_only_boring"` are equivalent and both may appear in real exports — accept either; preserve whichever the input used on round-trip. `"hidden"` = hidden from both player and AI. |
| `description` | string | Editable | Free-form description of what the item represents. May contain `<<template_variables>>` |
| `updateInstructions` | string | Editable | Instructions to the AI for when/how to update this item. Empty string is valid (no auto-update) |
| `initialValue` | string | Editable | World-default initial value. Per-character overrides live in `possibleCharacters[*].initialTrackedItemValues` |
| `initialValueBasedOnPC` | string | Editable | One of: `"same"` (all characters share initial value), `"character"` (per-character defaults), `"player"` (player chooses at game start) |
| `autoUpdate` | boolean | Editable | Whether the AI updates this item automatically each turn |

**`initialPCValue` array form**: in `possibleCharacters[*].initialTrackedItemValues`, the `initialPCValue` may be a string OR a string array. When it is an array (e.g., `["0", "900", "5"]`), the values are the **set of available choices the player picks from** at character selection. Treat the array as an unordered set of valid options — not a [min, max, default] tuple or a distribution.

## 5 `triggerEvents[*]`

| Key | Type | Category | Notes |
|---|---|---|---|
| `id` | string | Platform | Unique ID |
| `name` | string | Editable | Author-facing name |
| `canTriggerMoreThanOnce` | boolean | Editable | If false, fires at most once per game |
| `advancedLogic` | boolean | Editable | If true, allows `category: "logic"` combinator in `triggerConditions` |
| `triggerOnStartOfGame` | boolean | Editable | Top-level boolean on the trigger (NOT a condition type). If true, fires before turn 0. |
| `triggerConditions` | object[] | Editable | Conditions that gate when this trigger fires. See `triggerConditions[*]` below. |
| `triggerEffects` | object[] | Editable | Effects applied when the trigger fires. See `triggerEffects[*]` below. |

**Note**: in the v2.1 fixture, prerequisites and blockers appear only as `triggerPrereqs` / `triggerBlockers` condition types under `triggerConditions` (see below). Whether top-level `prerequisites` / `blockers` fields are also accepted by the platform is unverified — the plugin emits only the condition-type form.

### `triggerConditions[*]`

Every condition has `id` (UUID), `category`, `data`, plus type-specific fields.

**`data` is polymorphic** — its shape depends entirely on `type`: a `string[]` for `triggerOnCharacter`/`triggerBlockers`/`triggerPrereqs`, an object for `triggerOnTrackedItem`, a formula string for `triggerOnRandomChance`, an integer for `triggerOnTurn`, a natural-language string for `triggerOnEvent`, and an object array for `category: "logic"`. Do not assume a uniform shape.

For `category: "condition"`, the condition has a `type`:

| Type | Data shape | Notes |
|---|---|---|
| `triggerOnCharacter` | `string[]` | Array of `characterId` values from `possibleCharacters` |
| `triggerOnTrackedItem` | `{inequality, requiredValue, trackedItemID, textComparison}` | `inequality` one of: `at_least`, `is_exactly`, `at_most`, `contains`. `requiredValue` may be a formula string like `"1d4+skill_charm"`. `trackedItemID` may reference a tracked-item ID OR a synthetic `skill_<name>` ID for skill comparisons. `textComparison` (e.g., `contains`) is used for text-type tracked items. The condition object also carries top-level `inequality` and `trackedItemID` fields duplicating those inside `data` — preserve both. |
| `triggerOnRandomChance` | `string` (formula) | Formula evaluated each turn, compared against a random number. E.g., `"15+round(turn_number%random)"` or a simple `"30"` for 30% |
| `triggerOnTurn` | `integer` | Fires when the current turn number ≥ the integer value of `data`. E.g., `data: 5` fires from turn 5 onward (combined with `canTriggerMoreThanOnce: false` for a one-shot; with `canTriggerMoreThanOnce: true` to repeat every eligible turn from that turn on). |
| `triggerOnEvent` | `string` | AI-evaluated condition. `data` is a free-form natural-language description of an event (e.g., `"Someone says the words 'dummy bunny' to you"`). The AI reads the narrative each turn and fires the trigger when it judges the described event has occurred. Use for events that cannot be reduced to a tracked-item comparison or random chance — anything requiring narrative judgment. Valid both as a top-level condition and as a sub-condition inside a `category: "logic"` block. |
| `triggerBlockers` | `string[]` | Array of trigger IDs that must NOT have fired. If any have, this trigger is blocked. |
| `triggerPrereqs` | `string[]` | Array of trigger IDs that must have fired first. |

For `category: "logic"`:

| Field | Type | Notes |
|---|---|---|
| `category` | `"logic"` | Marker |
| `operator` | `"and"` \| `"or"` | Combinator for the sub-conditions |
| `data` | object[] | Array of sub-conditions (recursive — sub-conditions are themselves condition objects) |
| `id` | string (UUID) | (same as regular condition) |

Logic conditions only render when `advancedLogic: true` is set on the trigger. The default trigger semantics outside logic is AND across all conditions.

### `triggerEffects[*]` — canonical list from v2.1 fixture

Every effect has `id` (UUID), `type`, and `data`. Some have additional top-level fields.

| Effect type | Data shape | Top-level extras | Description (from fixture values) |
|---|---|---|---|
| `effectShowMessage` | string | — | Show message to the player |
| `effectTellAIWhatToDo` | string | — | Instructs the AI what should happen on the next turn — equivalent to a player using Storyteller Mode issuing a directive. When this effect fires, it **temporarily disables** the Storyteller Mode input for that turn (the player cannot also issue a Storyteller directive on the same turn). |
| `effectGiveInfo` | string | — | Appends the effect text to `secretInfo`, which the AI considers when generating its response. Unlike `effectTellAIWhatToDo`, instructions in `secretInfo` are **not guaranteed to be followed** — the AI treats them as context rather than directives. Use for world-state facts the AI should be aware of; use `effectTellAIWhatToDo` when compliance is required. |
| `effectChangeBackground` | string | — | Replaces world `background` |
| `effectChangeMainInstructions` | string | — | Replaces world `instructions` |
| `effectChangeAuthorStyle` | string | — | Replaces world `authorStyle` |
| `effectChangeDescriptionInstructions` | string | — | Replaces world `descriptionRequest` |
| `effectChangeObjective` | string | — | Replaces world `objective` |
| `effectChangeFirstAction` | string | — | Replaces world `firstInput` |
| `effectChangePCName` | string | — | Renames the active player character |
| `effectChangePCDescription` | string | — | Replaces the active PC's description |
| `effectChangePCSkill` | `{name, amount, minmax, increase}` | — | `name`: skill name. `amount`: integer delta. `minmax`: cap (when increasing) or floor (when decreasing). `increase`: boolean direction. |
| `effectChangeVictoryCondition` | `{condition, text, alreadyFired}` | — | Replaces world `victoryCondition` |
| `effectChangeDefeatCondition` | `{condition, text, alreadyFired}` | — | Replaces world `defeatCondition` |
| `effectEndsGame` | boolean | — | End the game. `data: true` allows player continuation (victory-style); `data: false` ends with no continuation (defeat-style). |
| `effectModifyInstructionBlock` | `{id, content}` | — | Modifies an Extra Instruction Block by ID |
| `effectModifyKeywordBlock` | `{id, content, keywords}` | — | Modifies a Keyword Instruction Block by ID — replaces both content AND keywords |
| `effectSetTrackedItemValue` | `{action, newValue, replaceWith, trackedItemID}` | `trackedItemID` | `action` one of: `set`, `add` (append), `subtract` (remove if present), `replace` (string-replace). `replaceWith` is used only by `replace`. Both the data object AND the effect object carry `trackedItemID`. |
| `effectModifyTrackedItemDetails` | `{trackedItemID, override flags, new field values}` | `trackedItemID` | Modify the tracked item itself, not its value. The complete set of override flags (as of v2.1) is: `overrideName`, `overrideDescription`, `overrideUpdateInstructions`, `overrideVisibility`, `overrideAutoUpdate`. When a flag is true, the corresponding new value is applied. |
| `effectPresentChoice` | `{choices, message, updateMode, maxSelections, minSelections, selectionMode, valueDelimiter, targetTrackedItemId}` | — | Present a choice to the player. `choices` is newline-separated. `selectionMode`: `"single"` or `"multiple"`. `valueDelimiter`: `"newline"` or `"comma"` (how multi-selections are stored). `updateMode`: only `"replace"` is currently defined; the validator should warn (not error) on other values in case the platform adds new modes. `min/maxSelections`: integers or null. Result is written to `targetTrackedItemId`. Blocking — the game pauses until the player chooses. |
| `effectRequestInput` | `{inputMode, requestText, requiresInput, targetTrackedItemId}` | — | Request free-text input from the player. `inputMode`: `"multi"` (multiline) or presumably `"single"`. `requiresInput`: boolean. Result is written to `targetTrackedItemId`. Blocking, same as `effectPresentChoice`. |

**Forward compatibility**: the table above is the comprehensive set of effect types observed in v2.1 fixtures. Future schema versions may add new types. The validator must **warn** (not error) on unrecognized `type` values so unknown-but-platform-valid effects survive round-trips. The agent should refuse to emit unrecognized types until they appear in a verified fixture, but should leave existing unknown-type effects untouched when editing other fields of the world.

**v2.1 consolidation.** Pre-v2.1 worlds used a separate boolean field
`canContinueEndedGame` to control continuation behavior on an end-game
trigger. In v2.1 that field is gone — the `data` boolean of `effectEndsGame`
serves both roles. Authors familiar with the wiki's older documentation
will not find `canContinueEndedGame` in v2.1 fixtures.

## 6 Instruction blocks

Two distinct arrays, both editable. They differ by keyword presence:

`instructionBlocks[*]` — Extra Instruction Blocks (always active):

| Key | Type | Notes |
|---|---|---|
| `id` | string | Platform ID |
| `name` | string | Author-facing name |
| `content` | string | Instruction text |
| `selectedAIProfiles` | string[] (optional) | Present only when `enableAISpecificInstructionBlocks: true` is set on the world. Restricts the block to specific AI model names (e.g., `["smilodon"]`) |

`loreBookEntries[*]` — Keyword Instruction Blocks (keyword-triggered):

| Key | Type | Notes |
|---|---|---|
| `id` | string | Platform ID |
| `name` | string | Author-facing name |
| `content` | string | Instruction text — injected when a keyword is detected in recent narrative |
| `keywords` | string[] | Keywords/phrases that activate this block |

## 7 Player permissions

All six are top-level boolean fields. Platform defaults (used by `scaffold_world`):

| Field | Default | Purpose |
|---|---|---|
| `allowChangeCharacterName` | `true` | Player may rename their selected PC |
| `allowChangeCharacterDescription` | `true` | Player may edit their selected PC's description |
| `allowChangeCharacterSkills` | `false` | Player may redistribute skill points on their selected PC |
| `allowChangeCharacterItemValues` | `false` | Player may change per-character starting tracked-item values |
| `allowChangeCharacterPortrait` | `false` | Player may select an alternate generated portrait |
| `allowChangeCharacterNewPortrait` | `false` | Player may generate a new portrait |

## 8 Image prompt details (world + per-character)

`imagePromptDetails` (world-level) and `portraitPromptDetails` (per-character) have the same shape:

| Key | Type | Notes |
|---|---|---|
| `illustrGenre` | string | Genre/style descriptor (e.g., `"fantasy, colorful, whimsical, storybook"`) |
| `illustrClothes` | string | Clothing description |
| `illustrSetting` | string | Setting/background description |
| `illustrSubject` | string | Subject identifier (often the character/world name) |
| `illustrAppearance` | string | Physical appearance description |
| `illustrIsCharacter` | boolean | Whether this is a character portrait (vs scene) |
| `illustrExpressionPosition` | string | Expression/pose descriptor (e.g., `"smiling"`, `"calm"`) |

These are author-editable (the user provides the description); the platform uses them to drive image generation and stores resulting URLs in the parallel `*Image`/`*Portrait` fields. The plugin should treat the prompt details as editable and the URLs as platform-managed.

## 9 Template variable system

From the fixture's "Available Variables" instruction block, the platform supports `<<variable>>` interpolation in any text field. Variables include:

- `player_name` — current player character's name
- Any **tracked item** by name, snake-cased and lowercased: `Favorite Flavor` → `favorite_flavor`
- Any **skill** prefixed with `skill_` and lowercased: `Charm` → `skill_charm`
- `turn_number` — current turn integer
- `initial_<varname>` — initial value of a numerical variable
- `random` — float `0.0` ≤ x < `1.0`, three decimal places
- `XdY` — dice roll
- Math operators and functions: `+ - * /`, `trunc(x)`, `round(x)`, `abs(x)`, `x%y`

The plugin doesn't need to evaluate these (the platform does), but `validate_world` should at minimum verify referenced names exist (e.g., a `<<skill_baking>>` reference fails if no `Baking` skill is declared).

---
