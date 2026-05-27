# Agents

The plugin ships one agent: `world-architect.md`.

## How the agent is invoked

The agent is reached two ways, and they look different from the inside:

1. **Spawned as a subagent** for a freeform user request — e.g. *"build me a noir detective world"*, *"debug why my trigger doesn't fire"*. Claude routes the task to the agent via the Task tool. The agent receives the task in its initial prompt, works in its own context window, and returns one final report. There is no multi-turn interaction with the user during that run.
2. **Loaded inline by a slash command** (`/infinite-worlds-architect:new-world`, `:modify-world`, `:spinoff-world`). Each command file starts with `@${CLAUDE_PLUGIN_ROOT}/agents/world-architect.md`, which inlines the agent's system prompt into the main session. The main session adopts the agent's persona and then follows the command's specific workflow steps, *retaining* the ability to talk to the user turn-by-turn. This is essential for the field-by-field approval loop the commands rely on — a subagent cannot do that.

The substantive content of the agent's job is the same in both modes: edit-flow contract, source-of-truth hierarchy, wiki discipline, debugging playbook. The difference is purely whether multi-turn user interaction is available.

## When the agent fires automatically

The agent's `description` field carries the triggering examples. Claude will route to it for:

- World creation requests (*"I want to build a world set in..."*)
- Trigger / tracked-item debugging (*"My trigger doesn't fire..."*)
- Single-entity edits (*"Add an NPC to..."*)
- Infinite Worlds platform-mechanics questions that require schema/fixture/wiki research

For trivial one-liners (*"what's a tracked item?"*), Claude may answer inline rather than spawning the agent. That's expected — spawn cost is non-trivial.
