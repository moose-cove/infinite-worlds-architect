"""Build Probe E (scope level + model control + absent conditions key) from Probe B.

    python build_probe_e.py <probe-b-cap.json> <out.json>

Probe E carries exactly three questions, all deliberately minimal:

1. P10-followup — which LEVEL of ``initialValueBasedOnPC`` is fatal, the per-character
   entry or its backing tracked item? Two cells, each breaking the entry/item covariance
   that confounded Probes A and B:

       PE1: item "player"    + entry "character"  (entry deleted => item level is fatal)
       PE2: item "character" + entry "player"     (entry deleted => entry level is fatal)

   Both cells use plain-string ``initialPCValue`` — Probe B already cleared the array
   shape as a factor.

2. recommendedAIModel bogus control — ``"notarealmodel"``. Probe B showed "smilodon"
   is stored; this shows whether IW validates the field at all (kept verbatim / reset
   to null / import rejected).

3. Q10 — a trigger with NO ``triggerConditions`` key at all (not ``[]``). Probe D
   proved ``[]`` is runtime-dead; the absent-key variant was swapped out of Probe D
   while bisecting the missing-description editor failure and has never been imported
   or played. A control trigger with an always-true ``triggerOnPawScript`` gate proves
   the trigger machinery fires each turn in this world.
"""

from __future__ import annotations

import json
import sys


def tracked_item(id_: str, name: str, var: str, desc: str, **over: object) -> dict:
    item = {
        "id": id_,
        "name": name,
        "positionInList": 0,
        "dataType": "text",
        "visibility": "everyone",
        "description": desc,
        "updateInstructions": "",
        "formatExample": "",
        "enforceFormat": False,
        "formatSchema": "",
        "initialValue": "",
        "initialValueBasedOnPC": "same",
        "autoUpdate": False,
        "variableName": var,
        "driftAcknowledgedForName": None,
    }
    item.update(over)
    return item


def main() -> None:
    base_path, out_path = sys.argv[1], sys.argv[2]
    with open(base_path) as f:
        world = json.load(f)

    world["title"] = "SCHEMA PROBE E - scope level, model control, absent conditions key"
    world["description"] = (
        "Probe world: which level of initialValueBasedOnPC is fatal (entry vs item), "
        "whether a bogus recommendedAIModel survives, and whether a trigger with an "
        "absent triggerConditions key ever fires."
    )
    world["version"] = "1.00"
    world["recommendedAIModel"] = "notarealmodel"
    world["conditions"] = []
    world["designNotes"] = (
        "SCHEMA PROBE E. Two cells breaking the entry/item initialValueBasedOnPC "
        "covariance (P10-followup), a bogus recommendedAIModel control, and the Q10 "
        "absent-triggerConditions-key trigger with an always-true control gate. See "
        "probes/README.md in the infinite-worlds-architect repo for the read protocol."
    )

    world["trackedItems"] = [
        tracked_item(
            "PrbEScp01",
            "PE1 Item-Player Entry-Character",
            "pe1_item_player",
            "PROBE PE1: backing ITEM is scoped 'player', its per-character ENTRY is "
            "scoped 'character'. If this entry is deleted on import, the ITEM level "
            "is the fatal one (reading b).",
            positionInList=0,
            initialValueBasedOnPC="player",
        ),
        tracked_item(
            "PrbEScp02",
            "PE2 Item-Character Entry-Player",
            "pe2_item_character",
            "PROBE PE2: backing ITEM is scoped 'character', its per-character ENTRY is "
            "scoped 'player'. If this entry is deleted on import, the ENTRY level is "
            "the fatal one (reading a - what the validator assumes).",
            positionInList=1,
            initialValueBasedOnPC="character",
        ),
        tracked_item(
            "PrbENum01",
            "PE Anchor",
            "pe_anchor_n",
            "PROBE anchor: holds 3 so the control trigger's gate '$pe_anchor_n > 0' is "
            "always true. If the control never fires, nothing else is interpretable.",
            positionInList=2,
            dataType="number",
            initialValue="3",
        ),
    ]

    for pc in world["possibleCharacters"]:
        pc["initialTrackedItemValues"] = [
            {
                "id": "PrbEScp01",
                "visibility": "everyone",
                "name": "PE1 Item-Player Entry-Character",
                "initialPCValue": "PROBE PE1 SINGLE VALUE",
                "initialValueBasedOnPC": "character",
            },
            {
                "id": "PrbEScp02",
                "visibility": "everyone",
                "name": "PE2 Item-Character Entry-Player",
                "initialPCValue": "PROBE PE2 SINGLE VALUE",
                "initialValueBasedOnPC": "player",
            },
        ]

    world["triggerEvents"] = [
        {
            # Q10: deliberately NO "triggerConditions" key.
            "id": "PrbEQ10x1",
            "name": "Q10 absent conditions key",
            "triggerEffects": [
                {
                    "id": "55550000-5555-4555-8555-555500000001",
                    "data": "PROBE Q10 ABSENT-KEY FIRED.",
                    "type": "effectShowMessage",
                }
            ],
            "canTriggerMoreThanOnce": True,
        },
        {
            "id": "PrbECtl01",
            "name": "PE Control always-true gate",
            "triggerConditions": [
                {
                    "id": "55550000-5555-4555-8555-555500000101",
                    "category": "condition",
                    "type": "triggerOnPawScript",
                    "data": "$pe_anchor_n > 0",
                }
            ],
            "triggerEffects": [
                {
                    "id": "55550000-5555-4555-8555-555500000002",
                    "data": "PROBE PE CONTROL FIRED.",
                    "type": "effectShowMessage",
                }
            ],
            "canTriggerMoreThanOnce": True,
        },
    ]

    with open(out_path, "w") as f:
        json.dump(world, f, indent=2)
        f.write("\n")
    print(f"wrote {out_path}")
    assert "triggerConditions" not in world["triggerEvents"][0], "Q10 key must be absent"


if __name__ == "__main__":
    main()
