"""Build Probe C (PawScript malformed input + firedThisTurn semantics) from Probe E.

    python build_probe_c.py <probe-e-scope-q10.json> <out.json>

Probe C carries three questions plus one cheap rider:

1. P14 (import side) — what does IW do with a MALFORMED ``triggerOnPawScript``?
   Six triggers, one condition each, against one text item ``probe_flavor`` = "Lemon".
   IW's known failure mode is silent deletion, so the read is the export diff: which
   conditions come back, and which are gone.

       P14a  "$probe_flavor = \"Lemon\""      control — must survive (fixture-proven shape)
       P14b  ""                               blank data
       P14c  (no ``data`` key at all)         absent data
       P14d  "$no_such_item = 1"              undeclared $name
       P14e  "$probe_flavor"                  non-boolean expression
       P14f  "<<probe_flavor>> = \"Lemon\""   legacy <<…>> interpolation

2. P2 (runtime) — does ``firedThisTurn: true`` narrow a prereq/blocker gate from
   "the listed trigger fired at ANY point" to "…fired THIS turn"? A one-shot anchor
   fires on turn 1 and never again, so from turn 2 it has fired-at-some-point but not
   fired-this-turn. Four repeatable consumers split that:

       P2a  prereqs  firedThisTurn=true     H1: fires turn 1 only
       P2b  prereqs  firedThisTurn=false    H1: fires every turn  (control)
       P2c  blockers firedThisTurn=true     H1: blocked turn 1, fires turn 2+
       P2d  blockers firedThisTurn=false    H1: blocked from turn 1 on (control)

   Under H0 (the field is inert / platform-managed) P2a ≡ P2b and P2c ≡ P2d.
   The anchor is FIRST in ``triggerEvents`` because Probe D Q6 established that
   list order is pass order, so it fires before its consumers evaluate on turn 1.

3. P15 rider (import side) — an undeclared ``$name`` inside a ``triggerOnRandomChance``
   formula: kept verbatim, or deleted like a malformed condition? One trigger.

4. Auto-create rider (import side) — Probe E showed a "character"-scoped item that
   arrives with NO per-character entry gets one auto-created, but its cell had an
   empty ``initialValue`` so it could not show WHERE the auto-created value comes
   from. ``PrbCInh01`` is "character"-scoped, carries a non-empty ``initialValue``
   and has no entry: if the export's auto-created entry carries that string, the
   item-level value seeds it; if it is "", the entry starts blank and
   TRACKED_ITEMS.md's "set the value explicitly" advice is load-bearing.
"""

from __future__ import annotations

import json
import sys

EFF = "66660000-6666-4666-8666-6666000000"
CND = "66660000-6666-4666-8666-6666000001"


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


def trigger(id_: str, name: str, msg: str, conditions: list[dict], repeat: bool = True) -> dict:
    return {
        "id": id_,
        "name": name,
        "triggerConditions": conditions,
        "triggerEffects": [{"id": f"{EFF}{id_[-2:]}", "data": msg, "type": "effectShowMessage"}],
        "canTriggerMoreThanOnce": repeat,
    }


def pawscript(seq: str, data: object = ...) -> dict:
    """One triggerOnPawScript condition. Pass no `data` to omit the key entirely (P14c)."""
    cond = {"id": f"{CND}{seq}", "category": "condition", "type": "triggerOnPawScript"}
    if data is not ...:
        cond["data"] = data
    return cond


def gate(seq: str, ctype: str, key: str, fired_this_turn: bool) -> dict:
    return {
        "id": f"{CND}{seq}",
        "category": "condition",
        "type": ctype,
        "data": {key: ["PrbCAnch01"], "firedThisTurn": fired_this_turn},
    }


def main() -> None:
    base_path, out_path = sys.argv[1], sys.argv[2]
    with open(base_path) as f:
        world = json.load(f)

    world["title"] = "SCHEMA PROBE C - PawScript malformed input, firedThisTurn"
    world["description"] = (
        "Probe world: what IW does with malformed triggerOnPawScript conditions on import, "
        "and whether firedThisTurn narrows a prereq/blocker gate to the current turn."
    )
    world["version"] = "1.00"
    world["recommendedAIModel"] = None
    world["conditions"] = []
    world["designNotes"] = (
        "SCHEMA PROBE C. Six malformed-triggerOnPawScript cells (P14a-f, read from the "
        "export diff), a firedThisTurn 2x2 over prereqs and blockers against a one-shot "
        "anchor (P2, read in play), an undeclared-$name random-chance formula (P15 rider), "
        "and a character-scoped item with a non-empty initialValue and no per-character "
        "entry (auto-create rider). See probes/README.md in the infinite-worlds-architect "
        "repo for the read protocol."
    )

    world["trackedItems"] = [
        tracked_item(
            "PrbCFlav01",
            "PC Flavor",
            "probe_flavor",
            "PROBE P14 target: holds 'Lemon' so the control condition "
            "'$probe_flavor = \"Lemon\"' is true. Every P14 cell reads this item.",
            positionInList=0,
            initialValue="Lemon",
        ),
        tracked_item(
            "PrbCNum01",
            "PC Anchor Number",
            "pc_anchor_n",
            "PROBE anchor value: holds 3 so the P2 anchor's gate '$pc_anchor_n > 0' is "
            "always true. If the anchor never fires, no P2 cell is interpretable.",
            positionInList=1,
            dataType="number",
            initialValue="3",
        ),
        tracked_item(
            "PrbCInh01",
            "PC Inherit Seed",
            "pc_inherit",
            "PROBE auto-create rider: this item is scoped 'character' and carries a "
            "non-empty initialValue, but the player character has NO per-character entry "
            "for it. If the export's auto-created entry carries this string, the item's "
            "initialValue seeds it; if it is empty, it does not.",
            positionInList=2,
            initialValue="PROBE INHERIT SEED",
            initialValueBasedOnPC="character",
        ),
    ]

    # No per-character entries: the auto-create rider needs the "character"-scoped item to
    # arrive without one, and the other two items are "same"-scoped (Probe E showed those
    # never get an entry auto-created).
    for pc in world["possibleCharacters"]:
        pc["initialTrackedItemValues"] = []

    world["triggerEvents"] = [
        # --- P2: the anchor must be first so it fires before its consumers evaluate.
        trigger(
            "PrbCAnch01",
            "P2 Anchor one-shot",
            "PROBE P2 ANCHOR FIRED.",
            [pawscript("01", "$pc_anchor_n > 0")],
            repeat=False,
        ),
        trigger(
            "PrbCP2a01",
            "P2a prereq firedThisTurn true",
            "PROBE P2a FIRED (prereq, firedThisTurn=true).",
            [gate("02", "triggerPrereqs", "prereqs", True)],
        ),
        trigger(
            "PrbCP2b01",
            "P2b prereq firedThisTurn false",
            "PROBE P2b FIRED (prereq, firedThisTurn=false, control).",
            [gate("03", "triggerPrereqs", "prereqs", False)],
        ),
        trigger(
            "PrbCP2c01",
            "P2c blocker firedThisTurn true",
            "PROBE P2c FIRED (blocker, firedThisTurn=true).",
            [gate("04", "triggerBlockers", "blockers", True)],
        ),
        trigger(
            "PrbCP2d01",
            "P2d blocker firedThisTurn false",
            "PROBE P2d FIRED (blocker, firedThisTurn=false, control).",
            [gate("05", "triggerBlockers", "blockers", False)],
        ),
        # --- P14: malformed triggerOnPawScript. Read from the export diff.
        trigger(
            "PrbCP14a1",
            "P14a control well-formed",
            "PROBE P14a FIRED (control).",
            [pawscript("06", '$probe_flavor = "Lemon"')],
        ),
        trigger(
            "PrbCP14b1",
            "P14b blank data",
            "PROBE P14b FIRED (blank data).",
            [pawscript("07", "")],
        ),
        trigger(
            "PrbCP14c1",
            "P14c absent data key",
            "PROBE P14c FIRED (absent data key).",
            [pawscript("08")],
        ),
        trigger(
            "PrbCP14d1",
            "P14d undeclared name",
            "PROBE P14d FIRED (undeclared $name).",
            [pawscript("09", "$no_such_item = 1")],
        ),
        trigger(
            "PrbCP14e1",
            "P14e non-boolean expression",
            "PROBE P14e FIRED (non-boolean).",
            [pawscript("10", "$probe_flavor")],
        ),
        trigger(
            "PrbCP14f1",
            "P14f legacy interpolation",
            "PROBE P14f FIRED (legacy <<>> form).",
            [pawscript("11", '<<probe_flavor>> = "Lemon"')],
        ),
        # --- P15 rider: undeclared $name inside a random-chance formula.
        trigger(
            "PrbCP15g1",
            "P15 rider undeclared name in chance formula",
            "PROBE P15 RIDER FIRED (undeclared $name in chance formula).",
            [
                {
                    "id": f"{CND}12",
                    "category": "condition",
                    "type": "triggerOnRandomChance",
                    "data": "$no_such_item",
                }
            ],
        ),
    ]

    p14c = next(t for t in world["triggerEvents"] if t["id"] == "PrbCP14c1")
    assert "data" not in p14c["triggerConditions"][0], "P14c must omit its data key"

    with open(out_path, "w") as f:
        json.dump(world, f, indent=2)
        f.write("\n")
    print(
        f"wrote {out_path}: {len(world['triggerEvents'])} triggers, "
        f"{len(world['trackedItems'])} tracked items"
    )


if __name__ == "__main__":
    main()
