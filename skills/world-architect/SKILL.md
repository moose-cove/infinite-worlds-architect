---
name: world-architect
description: Author, edit, debug, or explain Infinite Worlds world JSON and platform behavior, or search Community Worlds. Use for world files, triggers, tracked items, characters, validator errors, schema questions, and community world discovery.
---

# World architect

Use the `iw-json-tools` MCP server and the reference library at the plugin root. For a guided creation, modification, spinoff, or sequel, also load the matching skill in `../new-world/`, `../modify-world/`, `../spinoff-world/`, or `../sequel-world/`.

## Sources

Trust `../../references/world_v2.4.schema.json` for structure, then `../../example-world-schema-v2.4.json` for actual field shapes, then `../../references/WORLD_JSON_SCHEMA_v2.4.md`. Use `../../references/README.md` to select field and pattern notes. For runtime behavior, read `../../references/mechanics/AI_RUNTIME_MECHANICS.md`. Read `../../references/mechanics/PAWSCRIPT.md` before editing scripts, `../../references/fields/YAML_TRACKED_ITEMS.md` before adding YAML tracked items, and `../../references/guidance/CHARACTER_AUTHORING_GUARDRAILS.md` before editing characters.

The Infinite Worlds wiki can add context. Cross-check claims that affect JSON shape or behavior against the schema and fixture, and identify wiki-only claims as such.

## Search Community Worlds

Use `search_community_worlds` for live catalog searches. The user can revise `text`, `include_tags`, `exclude_tags`, `match_all_tags`, `mature`, `nsfw`, `sort`, and `page` independently. A missing mature or NSFW filter includes both values. Use `get_community_world_details` for a full description and metadata, and `get_community_world_json` for the original world JSON. These tools read the site without copying a world into the user's Infinite Worlds account.

If authentication is missing or expired, direct the user to run `iw-community-auth login` in a local terminal. It prompts locally and stores credentials in the system keychain for session renewal. `iw-community-auth import-chrome --port 9222` imports an existing debug Chrome session once, but does not enable automatic renewal. Never request a password or session cookie in chat. The site's Anvil RPC is private, so report protocol failures plainly rather than guessing at results.

## Edit a world

1. Resolve user paths to absolute paths before calling an MCP world tool. The server has a separate working directory.
2. When modifying an existing world, call `make_draft_world(source_path)` first. Work only on its returned draft path. For spinoffs and sequels, pass the confirmed target path as the second argument. Keep the source as the comparison baseline.
3. Read the working JSON. Inspect relevant fields with `read_world_field`; use `get_schema_summary` and the matching reference before planning unfamiliar shapes.
4. Mint entity IDs with `mint_ids`. Ask the author for character `img_appearance` and `img_clothing`; leave them blank until supplied. Preserve unknown fields and `schemaVersion` by making targeted edits to the working JSON.
5. Present each proposed field change and get the author's approval before applying it. Apply changes to the same file sequentially.
6. Run `validate_world` after each batch and each script edit. Resolve errors and rerun until clean. Run `audit_world` for substantive edits and report its findings.

For new YAML tracked items, use a unique snake_case `variableName` and match nested `formatSchema` to the data. PawScript may mutate only declared tracked items; scripts roll back on failure. Use the v2.4 trigger shapes and requirements in `../../references/fields/TRIGGER_EVENTS.md`, including object shaped prereqs/blockers, nonempty `textComparison`, declared event names, and nonempty PawScript conditions.

## Diagnose a world

Read the current file, run `validate_world` and `audit_world`, then inspect the failing entity. For trigger behavior read `../../references/fields/TRIGGER_EVENTS.md` and the runtime mechanics; for state updates read `../../references/fields/TRACKED_ITEMS.md`; for missing lore read `../../references/fields/KEYWORD_INSTRUCTION_BLOCKS.md`; for instruction placement read `../../references/guidance/FIELD_ALLOCATION_STRATEGY.md`. Compare a working and broken version with `compare_worlds` and `get_diff_summary` when both exist. Explain the cause in Infinite Worlds terms and cite the source of the behavior.

Check menu-backed tracked items before judging a condition: an array `initialPCValue` is a menu whose chosen value becomes active, not a set of simultaneous values. Keep per-character initial values on character-scoped items. Treat unknown condition or effect types as questions to check against schema and fixture.
