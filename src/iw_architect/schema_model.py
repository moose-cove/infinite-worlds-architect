"""Schema model — structured metadata about the world schema.

Used by get_schema_summary() so the agent can introspect available entity types, fields,
and enum values without parsing the Markdown schema doc.
"""

from __future__ import annotations

SCHEMA_SUMMARY = {
    "schemaVersion": 2.1,
    "topLevelFields": {
        "schemaVersion": {"type": "number", "category": "platform", "required": True},
        "title": {"type": "string", "category": "editable", "required": True},
        "description": {"type": "string", "category": "editable"},
        "background": {"type": "string", "category": "editable"},
        "instructions": {"type": "string", "category": "editable"},
        "authorStyle": {"type": "string", "category": "editable"},
        "firstInput": {"type": "string", "category": "editable"},
        "objective": {"type": "string", "category": "editable"},
        "mature": {"type": "boolean", "category": "editable"},
        "nsfw": {"type": "boolean", "category": "editable", "note": "Requires mature:true"},
        "contentWarnings": {"type": "string", "category": "editable"},
        "descriptionRequest": {"type": "string", "category": "editable"},
        "evaluationRequest": {"type": "string", "category": "editable"},
        "summaryRequest": {"type": "string", "category": "editable"},
        "hideSkillSystem": {"type": "boolean", "category": "editable"},
        "imageModel": {"type": "string", "category": "editable"},
        "imageStyle": {"type": "string", "category": "editable"},
        "imageStyleCharacterPre": {"type": "string", "category": "editable"},
        "imageStyleCharacterPost": {"type": "string", "category": "editable"},
        "imageStyleNonCharacterPre": {"type": "string", "category": "editable"},
        "imageStyleNonCharacterPost": {"type": "string", "category": "editable"},
        "illustrationStyleCharacterLowPriority": {"type": "string", "category": "editable"},
        "illustrationStyleCharacterHighPriority": {"type": "string", "category": "editable"},
        "illustrationStyleNonCharacterLowPriority": {"type": "string", "category": "editable"},
        "illustrationStyleNonCharacterHighPriority": {"type": "string", "category": "editable"},
        "enableAISpecificInstructionBlocks": {"type": "boolean", "category": "editable"},
        "recommendedAIModel": {"type": "string|null", "category": "editable"},
        "charSelectText": {"type": "string", "category": "editable"},
        "designNotes": {"type": "string", "category": "editable", "note": "NOT sent to AI"},
        "skills": {"type": "string[]", "category": "editable"},
        "victoryCondition": {"type": "object|null", "category": "editable+platform"},
        "defeatCondition": {"type": "object|null", "category": "editable+platform"},
        "imagePromptDetails": {"type": "object", "category": "hybrid"},
        "permissionsOnceShared": {"type": "object", "category": "editable"},
        "allowChangeCharacterName": {"type": "boolean", "category": "editable", "default": True},
        "allowChangeCharacterDescription": {
            "type": "boolean",
            "category": "editable",
            "default": True,
        },
        "allowChangeCharacterSkills": {"type": "boolean", "category": "editable", "default": False},
        "allowChangeCharacterItemValues": {
            "type": "boolean",
            "category": "editable",
            "default": False,
        },
        "allowChangeCharacterPortrait": {
            "type": "boolean",
            "category": "editable",
            "default": False,
        },
        "allowChangeCharacterNewPortrait": {
            "type": "boolean",
            "category": "editable",
            "default": False,
        },
        "possibleCharacters": {"type": "object[]", "category": "editable+platform"},
        "NPCs": {"type": "object[]", "category": "editable"},
        "trackedItems": {"type": "object[]", "category": "editable"},
        "triggerEvents": {"type": "object[]", "category": "editable+platform"},
        "instructionBlocks": {"type": "object[]", "category": "editable"},
        "loreBookEntries": {"type": "object[]", "category": "editable"},
        "version": {"type": "string", "category": "platform"},
        "autoAdvanceVersion": {"type": "boolean", "category": "editable"},
        "favorite": {"type": "boolean", "category": "platform"},
        "previewImage": {"type": "string", "category": "platform"},
        "fullSizePreviewImage": {"type": "string", "category": "platform"},
        "previewImageOptions": {"type": "string[]", "category": "platform"},
        "fullSizePreviewImageOptions": {"type": "string[]", "category": "platform"},
        "currentPreviewImageIndex": {"type": "number", "category": "platform"},
    },
    "entityTypes": {
        "possibleCharacters": {
            "description": "Player-selectable characters",
            "idField": "characterId",
            "idFormat": "8-char platform-assigned",
            "fields": {
                "name": {"type": "string", "required": True},
                "description": {"type": "string"},
                "characterId": {"type": "string", "category": "platform"},
                "skills": {"type": "object", "note": "Keys must match world-level skills"},
                "portrait": {"type": "string", "category": "platform"},
                "portraitPromptDetails": {"type": "object"},
                "initialTrackedItemValues": {"type": "object[]"},
            },
        },
        "NPCs": {
            "description": "Non-player characters",
            "idField": "id",
            "idFormat": "9-char platform-assigned",
            "fields": {
                "id": {"type": "string", "category": "platform"},
                "positionInList": {"type": "number", "required": True},
                "name": {"type": "string", "required": True},
                "detail": {"type": "string"},
                "one_liner": {"type": "string"},
                "appearance": {"type": "string"},
                "location": {"type": "string"},
                "secret_info": {"type": "string"},
                "names": {"type": "string[]"},
                "img_appearance": {"type": "string"},
                "img_clothing": {"type": "string"},
            },
        },
        "trackedItems": {
            "description": "World state variables",
            "idField": "id",
            "idFormat": "9-char platform-assigned",
            "fields": {
                "id": {"type": "string", "category": "platform"},
                "name": {"type": "string", "required": True},
                "positionInList": {"type": "number", "required": True},
                "dataType": {
                    "type": "string",
                    "required": True,
                    "enum": ["text", "number", "xml"],
                },
                "visibility": {
                    "type": "string",
                    "required": True,
                    "enum": ["everyone", "ai_only", "ai_only_boring", "player_only", "hidden"],
                },
                "description": {"type": "string"},
                "updateInstructions": {"type": "string"},
                "initialValue": {"type": "string"},
                "initialValueBasedOnPC": {
                    "type": "string",
                    "enum": ["same", "character", "player"],
                },
                "autoUpdate": {"type": "boolean", "required": True},
            },
        },
        "triggerEvents": {
            "description": "Conditional events that fire when conditions are met",
            "idField": "id",
            "idFormat": "8-char platform-assigned",
            "fields": {
                "id": {"type": "string", "category": "platform"},
                "name": {"type": "string", "required": True},
                "canTriggerMoreThanOnce": {"type": "boolean"},
                "advancedLogic": {"type": "boolean", "note": "Enables logic conditions"},
                "triggerOnStartOfGame": {"type": "boolean"},
                "triggerConditions": {"type": "object[]"},
                "triggerEffects": {"type": "object[]", "required": True},
            },
        },
        "instructionBlocks": {
            "description": "Always-active extra instruction blocks",
            "idField": "id",
            "idFormat": "9-char platform-assigned",
            "fields": {
                "id": {"type": "string", "required": True},
                "name": {"type": "string", "required": True},
                "content": {"type": "string", "required": True},
                "selectedAIProfiles": {
                    "type": "string[]",
                    "note": "Only when enableAISpecificInstructionBlocks is true",
                },
            },
        },
        "loreBookEntries": {
            "description": "Keyword-triggered instruction blocks",
            "idField": "id",
            "idFormat": "9-char platform-assigned",
            "fields": {
                "id": {"type": "string", "required": True},
                "name": {"type": "string", "required": True},
                "content": {"type": "string", "required": True},
                "keywords": {"type": "string[]", "required": True},
            },
        },
    },
    "conditionTypes": {
        "triggerOnCharacter": {
            "data": "string[] (characterId values)",
            "description": "Fires only for specific player characters",
        },
        "triggerOnTrackedItem": {
            "data": "{inequality, requiredValue, trackedItemID, textComparison}",
            "description": "Fires based on tracked item or skill value comparison",
            "inequalities": ["at_least", "is_exactly", "at_most", "contains"],
        },
        "triggerOnRandomChance": {
            "data": "string (formula, e.g. '30' for 30%)",
            "description": "Fires with a random probability each turn",
        },
        "triggerOnTurn": {
            "data": "integer (turn number)",
            "description": "Fires when current turn >= data value",
        },
        "triggerOnEvent": {
            "data": "string (natural-language event description)",
            "description": "AI-evaluated: fires when AI judges the described event occurred",
        },
        "triggerPrereqs": {
            "data": "string[] (trigger IDs that must have fired)",
            "description": "Gates on prior trigger execution",
        },
        "triggerBlockers": {
            "data": "string[] (trigger IDs that must NOT have fired)",
            "description": "Blocked if any listed trigger has fired",
        },
        "logic": {
            "operator": "and|or",
            "data": "object[] (sub-conditions, recursive)",
            "description": "Combinator — requires advancedLogic: true on the trigger",
        },
    },
    "effectTypes": {
        "effectShowMessage": {"data": "string", "description": "Show message to player"},
        "effectTellAIWhatToDo": {
            "data": "string",
            "description": "Directive to the AI for next turn",
        },
        "effectGiveInfo": {
            "data": "string",
            "description": "Append to secretInfo (not guaranteed to be followed)",
        },
        "effectChangeBackground": {"data": "string", "description": "Replace world background"},
        "effectChangeMainInstructions": {
            "data": "string",
            "description": "Replace world instructions",
        },
        "effectChangeAuthorStyle": {"data": "string", "description": "Replace world authorStyle"},
        "effectChangeDescriptionInstructions": {
            "data": "string",
            "description": "Replace descriptionRequest",
        },
        "effectChangeObjective": {"data": "string", "description": "Replace world objective"},
        "effectChangeFirstAction": {"data": "string", "description": "Replace world firstInput"},
        "effectChangePCName": {"data": "string", "description": "Rename active player character"},
        "effectChangePCDescription": {
            "data": "string",
            "description": "Replace active PC description",
        },
        "effectChangePCSkill": {
            "data": "{name, amount, minmax, increase}",
            "description": "Modify a PC skill value",
        },
        "effectChangeVictoryCondition": {
            "data": "{condition, text, alreadyFired}",
            "description": "Replace victory condition (alreadyFired must be false)",
        },
        "effectChangeDefeatCondition": {
            "data": "{condition, text, alreadyFired}",
            "description": "Replace defeat condition (alreadyFired must be false)",
        },
        "effectModifyInstructionBlock": {
            "data": "{id, content}",
            "description": "Modify an instruction block by ID",
        },
        "effectModifyKeywordBlock": {
            "data": "{id, content, keywords}",
            "description": "Modify a lore book entry by ID (replaces both content and keywords)",
        },
        "effectSetTrackedItemValue": {
            "data": "{action, newValue, replaceWith, trackedItemID}",
            "topLevelFields": ["trackedItemID"],
            "actions": ["set", "add", "subtract", "replace"],
            "description": "Set or modify a tracked item's value",
        },
        "effectModifyTrackedItemDetails": {
            "data": (
                "{trackedItemID, overrideName, overrideDescription, "
                "overrideUpdateInstructions, overrideVisibility, overrideAutoUpdate, "
                "name?, description?, updateInstructions?, visibility?, autoUpdate?}"
            ),
            "topLevelFields": ["trackedItemID"],
            "description": "Modify tracked item metadata (not its value)",
        },
        "effectPresentChoice": {
            "data": (
                "{choices, message, updateMode, maxSelections, minSelections, "
                "selectionMode, valueDelimiter, targetTrackedItemId}"
            ),
            "description": "Present player a choice; result saved to tracked item (blocking)",
        },
        "effectRequestInput": {
            "data": "{inputMode, requestText, requiresInput, targetTrackedItemId}",
            "description": "Request free-text input from player (blocking)",
        },
    },
    "templateVariables": {
        "builtin": ["player_name", "turn_number", "random"],
        "trackedItems": "snake_case(item_name) — e.g., 'Favorite Flavor' → favorite_flavor",
        "skills": "skill_<snake_case(skill_name)> — e.g., 'Baking' → skill_baking",
        "initial": "initial_<varname> — initial value of any numerical variable",
        "dice": "XdY — e.g., 3d6, 1d20",
        "math": "+ - * / trunc(x) round(x) abs(x) x%y",
    },
}
