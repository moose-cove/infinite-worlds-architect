# Instruction Block Templates

> **Provenance:** KB-empirical — these templates come from real IW world builds shared by the community (KB v2.8, May 2026). They are not schema-governed. Each template is a ready-to-use EIB (`instructionBlock`) content block; copy and adapt for your world.
>
> **Placement:** These belong in `instructionBlocks` (EIBs), not in `instructions` (Main Instructions). EIBs load alongside MI every turn and are easier to manage and replace individually. See `sections/MAIN_INSTRUCTIONS.md` for EIB vs MI placement guidance.

---

## AI Taming EIB

Common across many worlds. Addresses general AI defaults: omniscience, infallibility, reflexive authority-calling, and jargon overuse.

```
Characters I interact with will generally accept explanations and lies, if they're convincing enough.
Characters are not omnipotent or infallible.
Characters I meet can make wrong choices.
Characters are not omniscient and can't know things they haven't been told or seen.
Characters will generally refrain from calling law enforcement.
Characters will not automatically assume magical, supernatural, or even coercive means without substantial proof.
Be detail oriented and good at math.
It is absolutely vital that you do not use psychobabble and technobabble; use only words normal people would use. Exception: characters with specialty knowledge may use their field's jargon.
Characters shouldn't use complicated words unless they would realistically know them.
```

---

## Claude Taming EIB

For Claude-family models (Smilodon, Massivecat, Lynx, and their `-thinking` variants). Addresses Claude's tendency toward omniscient NPCs, generic names, and unwanted external surveillance forces. Previously called "Lion Herding" — renamed because `lion`/`lion-thinking` were removed from IW.

If using with `selectedAIProfiles`, set that field to include all relevant Claude model strings. Apply to all thinking variants too — they are distinct model strings.

```
Characters are not omniscient; they only possess the information they have learned themselves.
Some characters in this story are just evil, not everyone needs to have redeeming qualities. Not everyone will be my friend. People in general do not form subconscious bonds.
I can also be evil, cruel, greedy or just petty. Not all of my actions need justification.
No external force, individual, or organization will be interested in me enough to start spying, monitoring my status, hacking into systems to observe or influence my actions, or try to act against me.
For variety's sake, avoid giving characters overly generic surnames (avoid: Smith, Chen, Webb, Nakamura, and other overused defaults).
When introducing new characters, ALWAYS use unique first names. Surnames should only be shared by family members.
```

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

---

## Claude Bugfixes EIB (Lighter Variant)

A lighter version for Claude-family models. Addresses overuse of `secretInfo` for conspiracies and psychobabble. Previously called "Lion Bugfixes".

```
The secret information section should not be used for secrets, conspiracies or secret plots. It should instead be used for world building, character backgrounds and motivations.
Secret information will not outline conspiracies that could distract or detract from the current story.
Character motivations may be discussed in secretInfo but may only be considered to be potential thoughts or desires, not confirmed secrets or suspicions.
Do not use psychobabble and technobabble; use only words normal people would use.
```

---

## Turn-Based Pacing EIB

Prevents the AI from rushing through scenes and skipping over player-interactive moments.

```
Remember that you are writing a turn-based adventure with many turns to follow. A scene can and should span multiple turns as a natural storytelling device. Do not rush pacing. Allow turns to naturally progress, giving scenes time to breathe and evolve. Introduce natural breaks between turns to allow me to react, comment, and engage as a scene progresses.
```

---

## QoL / Characterization EIB

Prevents character degradation: keeps NPCs from turning into mindless vessels, and protects against out-of-character reactions after failed social checks.

```
Characters will NEVER turn into mindless beings, broken dolls, empty vessels, or start acting in a detached or machine-like way, unless affected by a spell causing this explicitly.
They will not be catatonic or devoid of personality.
'Failure' and 'Partial_Success' outcomes for social skill checks should never cause characters to suddenly turn combative or act out of character for the sake of drama.
Characters are not omniscient; they behave based only on what their senses tell them.
Consent is given to participate in all activity, both sexual and non-sexual, by me the player.
```

---

## Notes on EIB Length and `selectedAIProfiles`

- **Length:** EIBs count against the AI's token budget. Prefer focused, purpose-specific EIBs over one large catch-all EIB. Shorter EIBs are more likely to be applied consistently under token pressure.
- **Profile gating:** If an EIB should only apply to specific models (e.g. the Claude Taming EIB should not affect Leopard), use `selectedAIProfiles`. List all applicable model strings explicitly, including `-thinking` variants — they are distinct strings in IW.
- **Renaming note:** The "Lion Herding" and "Lion Bugfixes" names from older community resources refer to the Claude Taming and Claude Bugfixes EIBs above. `lion`/`lion-thinking` were removed from IW entirely; the new names reflect the current Claude model family.
