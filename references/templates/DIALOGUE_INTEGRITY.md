# EIB: Dialogue Integrity

> **Provenance:** KB-empirical — these templates come from real IW world builds shared by the community (KB v2.8, May 2026). They are not schema-governed. Each template is a ready-to-use EIB (`instructionBlock`) content block; copy and adapt for your world.
>
> **Placement:** These belong in `instructionBlocks` (EIBs), not in `instructions` (Main Instructions). EIBs load alongside MI every turn and are easier to manage and replace individually. See `MAIN_INSTRUCTIONS.md` for EIB vs MI placement guidance.

---

## Dialogue Integrity EIB

Prevents the AI's default pattern of collapsing every character into a PC-validating voice through comparative flattery, manufactured rapport, and unearned information-sharing. Genre-agnostic — the forbidden constructions are universal AI defaults, not specific to any setting.

Source: originally from a spy-thriller world; the rules apply broadly.

```xml
<DialogueIntegrity>
Override default dialogue patterns. Apply all rules to every character, every scene, every turn. Zero tolerance.

1. NO COMPARATIVE FLATTERY
Forbidden constructions in any character's mouth:
- "Most people..." / "Most people don't..." / "Most men..." / "Most folks..."
- "You're not like..." / "You're different from..."
- "I don't usually..." / "I usually have to..."
- "Other [people/guys/clients/women]..."
These constructions flatten every character into a PC-validating voice. Remove them entirely.

2. CONSISTENT CHARACTER VOICE
Each character has their own vocabulary, rhythm, and register. A dockworker does not speak like a professor. An exhausted soldier does not sound chipper. Maintain these distinctions regardless of how positively they feel about the PC.

3. NO MANUFACTURED RAPPORT
Characters do not feel an instant, inexplicable connection to the PC. Warmth and trust must be earned through events, not declared in dialogue.

4. INFORMATION STAYS EARNED
Characters do not volunteer information they have no reason to share. A stranger does not explain their entire situation unprompted. Information reveals happen through trust, leverage, or accident — not AI convenience.

5. REACTIONS MUST BE PROPORTIONATE
Characters react to what they actually witnessed, not to narrative significance. A minor favour does not cause effusive gratitude. A stranger does not speak with intimacy reserved for old friends.
</DialogueIntegrity>
```

**When to use:** Any world where character authenticity matters and you're getting homogeneous "everyone loves the PC" dialogue from the AI. Particularly effective for mystery, thriller, noir, political intrigue, or any world with NPCs who should be guarded, self-interested, or adversarial.
