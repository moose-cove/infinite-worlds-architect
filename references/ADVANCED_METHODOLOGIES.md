# Advanced Methodologies

> **Provenance:** KB-empirical — techniques reverse-engineered from real IW worlds and community testing (KB v2.8, May 2026). Not schema-governed; apply where your world design warrants the complexity.

---

## Layered Knowledge Isolation

Guide for preventing NPCs from accessing information they should not know — the "omniscient NPC" problem in long games.

### The Problem

Over a long game, NPCs slowly leak. They reference events they never witnessed, name secrets they weren't told, or — worst — start using tracked-item vocabulary in dialogue ("I feel our trust has reached a comfortable level"). The root cause: the model sees the entire game state every turn and treats all of it as shared knowledge.

A single isolation rule in `instructions` (Main Instructions) holds for roughly 20 turns, then gets dropped under token pressure. **Effective isolation requires enforcement at multiple structural points.**

### Decision Gate — How Much Do You Need?

- **0–3 NPCs, little tracked state** → A single Knowledge Boundaries EIB (Layer 2 only) is usually enough.
- **3+ NPCs, ensemble cast, real secrets** → Layers 2 + 3 (per-turn gate + per-NPC fact ledger). The common case.
- **Factions / social strata / events that mean different things to different groups** → Add Layer 1 (Perception Tiers). This is where the design earns its keep.
- **Epoch-spanning game, NPCs return after long absence** → Add the return re-check (see Gotchas).

### The Four Layers

#### Layer 1 — Perception Tiers

*Could this NPC's position even reach this information, and does it mean the same thing to them?*

The macro gate. NPCs don't just have different facts — they live in different information ecosystems. A peasant sees "monsters attacked the village." A military order sees "a demon breached the eastern line." Same event; genuinely different fact based on position.

**IW implementation:**
- One `ai_only` tracked item (e.g. `PercTiers`) defining each tier and its *lens* (vocabulary, framing, information access).
- Assign each NPC to a tier in their `detail` field or a roster tracked item.
- One EIB rule: "Before rendering how any NPC perceives an event, first resolve their tier, then describe the event through that tier's lens."
- A tier does **not** upgrade because an NPC overheard something. Hearing a fact ≠ joining the ecosystem that produced it.

#### Layer 2 — Per-Turn Isolation

*Could she know it, was she told it, did she witness it?*

**The 3-question test** — before writing any NPC line that references tracked information:
1. Could she know this through her own senses?
2. Was she told it, aloud, in prose?
3. Did she witness the event?

If none of the three: **she doesn't know it.** Suspicion from observed behaviour is allowed; certainty needs evidence.

**IW implementation:**
- A "Knowledge Boundaries" EIB containing the full rule and any exceptions for the MC.
- A `KNOWLEDGE CHECK` step in your `[#OUTPUT]` pipeline EIB, between loading state and writing prose.
- WRONG/RIGHT examples in your `secretInfo` template:
  - WRONG: "My hygiene improved to presentable tier."
  - RIGHT: "Ugh, I actually don't hate how I look right now??"

#### Layer 3 — Per-NPC Fact Ledger

*What has this character actually acquired, and how?*

Layer 2 says what's allowed. Layer 3 *remembers* what each NPC has genuinely acquired, so secrets can travel realistically.

**IW implementation:**
- A `KNOWS` field per NPC (in a relationship-roster tracked item or dedicated TI). Each entry: `fact | source(witnessed/told/inferred) | confidence(direct/partial/rumor)`
- Track both directions for close pairs: `SHARED_PC` (what PC told them) and `SHARED_NPC` (what they told PC).
- A transferred fact gets `source=told, confidence=rumor`. It never upgrades the NPC's tier.

#### Layer 4 — Expression Gate

*Resolve it at the moment of writing.*

Before knowledge surfaces in prose or option text, resolve to one of three states:
- **KNOWN** — in ledger with adequate confidence → write it plainly.
- **SUSPICION** — partial/rumor or inferred from behaviour → write as a hunch, never certainty.
- **BLOCK** — not reachable → rewrite as a symptom ("you look pale," not "your health is at 2"), or cut it.

### The Pipeline

```
Tier reach check (Layer 1)  → could their tier even access this?
   ↓ pass
Witness check (Layer 2)     → know / told / witnessed?
   ↓ pass
Ledger lookup (Layer 3)     → is it recorded, with what provenance?
   ↓
Expression gate (Layer 4)   → KNOWN / SUSPICION / BLOCK
```

### Why Layering Beats One Good Rule

The most pressure-resistant placement for an isolation rule is **inside the relevant tracked item's own `updateInstructions`** — the model reads it at exactly the moment it's handling that data. Aim for 5–8 enforcement points: a global EIB, the output-pipeline check, `secretInfo` WRONG/RIGHT examples, and per-TI notes on every item holding tier labels, numbers, or player-private plans.

### Gotchas

- **Dramatic moments leak.** When the model wants a strong reaction, it reaches for knowledge the NPC shouldn't have. Correct in-session; the goal is rare edge cases, not perfection.
- **Player-private plans.** If the player wrote a goal in a TI but never said it aloud, NPCs must not react to it. Add "this is the player's private plan" to that TI's `updateInstructions`.
- **Returning NPCs.** When an NPC returns after a long absence, re-check their tier against the current world-state. Don't restore a stale tier.
- **Tiers ≠ importance.** A minor character can be high-access; a major character can be low-access. These are different axes.

### Minimum Viable Adoption

If you take one thing: **the 3-question test as a co-located rule in your high-risk TIs, plus a KNOWLEDGE CHECK in your output pipeline.** Add Perception Tiers only when your game has groups that genuinely understand the same events differently.
