# EIB Usage Notes

> **Provenance:** KB-empirical — these templates come from real IW world builds shared by the community (KB v2.8, May 2026). They are not schema-governed. Each template is a ready-to-use EIB (`instructionBlock`) content block; copy and adapt for your world.
>
> **Placement:** These belong in `instructionBlocks` (EIBs), not in `instructions` (Main Instructions). EIBs load alongside MI every turn and are easier to manage and replace individually. See `MAIN_INSTRUCTIONS.md` for EIB vs MI placement guidance.

---

## Notes on EIB Length and `selectedAIProfiles`

- **Length:** EIBs count against the AI's token budget. Prefer focused, purpose-specific EIBs over one large catch-all EIB. Shorter EIBs are more likely to be applied consistently under token pressure.
- **Profile gating:** If an EIB should only apply to specific models (e.g. the Claude Taming EIB should not affect Leopard), use `selectedAIProfiles`. List all applicable model strings explicitly, including `-thinking` variants — they are distinct strings in IW.
- **Renaming note:** The "Lion Herding" and "Lion Bugfixes" names from older community resources refer to the Claude Taming and Claude Bugfixes EIBs. `lion`/`lion-thinking` were removed from IW entirely; the new names reflect the current Claude model family.
