# Pattern: Phase Escalation via EIB Replacement

> **Provenance:** KB-empirical — reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). These patterns are not schema-governed; the schema does not mandate or restrict them. Apply where they fit your world's design.

---

## Pattern 1 — Phase Escalation via EIB Replacement

Use an `instructionBlock` (EIB) as a **mutable world-state container**. The EIB starts with phase-1 content; triggers fire at key story beats and use `effectModifyInstructionBlock` to replace the entire EIB content with the next phase. Each phase can describe different world conditions, faction states, NPC behaviours, or stakes.

**Why EIB replacement beats `effectChangeMainInstructions`:** EIBs are modular — one EIB handles phase-sensitive world state; others handle tone, character, or style that don't change. `effectChangeMainInstructions` is all-or-nothing; EIBs let you surgically swap only the evolving part. EIBs are also easier to manage in the world editor since each has a focused purpose.

**Pattern template:**

```json
{
  "id": "EibPhase1",
  "name": "World State",
  "content": "PHASE 1: [Describe conditions, faction states, environmental context for phase 1...]"
}
```

At the escalation trigger:

```json
{
  "id": "uuid",
  "type": "effectModifyInstructionBlock",
  "data": {
    "id": "EibPhase1",
    "content": "PHASE 2: [Describe escalated conditions...]"
  }
}
```

**Chaining phases:** Use `triggerPrereqs` on the Phase 3 trigger (require Phase 2 to have fired) to ensure the escalation chain fires in order even if timing conditions overlap.

**Naming convention:** Give the phase EIB a stable ID (e.g. `EibPhase1`) and a descriptive name (e.g. `"World State"`). Use `effectModifyInstructionBlock` to replace only its `content` — the `id` and `name` remain constant across all phases.
