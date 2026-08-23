"""Build probes/probe-d-pawscript-runtime.json from the round-2 world (same white room, PC and
instructions), per probes/probe-d-pawscript-runtime.md. Tracked items and triggers are replaced."""

import json
import sys
import uuid
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

w = json.loads(SRC.read_text())
w["title"] = "Probe D - PawScript runtime"
w["description"] = "Plugin probe world: trigger firing and PawScript runtime cells. Not a story."
w["version"] = "1.00"

GATE = {"category": "condition", "type": "triggerOnPawScript", "data": "$probe.n > 0"}

MARKERS = [
    "sog_empty",
    "sog_gated",
    "abs_key",
    "or_valid",
    "or_missing_right",
    "and_valid",
    "chance_if",
    "chance_bare_100",
    "chance_bare_0",
    "chance_additive",
    "chance_game_turn",
    "chance_bare_turn",
    "cond_same_turn",
    "order_keys",
    "late_created",
    "err_ran",
    "prereq_after_error",
    "prereq_after_ok",
    "deep_create",
    "dyn_create",
]

w["trackedItems"] = [
    {
        "id": "PrDProbe0",
        "name": "Probe",
        "description": "Fixed test values (n=3, z=0, hundred=100, flag=0).",
        "positionInList": 0,
        "dataType": "yaml",
        "variableName": "probe",
        "visibility": "everyone",
        "updateInstructions": "Never modify this item. It is a fixed test fixture.",
        "initialValue": "n: 3\nz: 0\nhundred: 100\nflag: 0",
        "initialValueBasedOnPC": "same",
        "autoUpdate": False,
        "enforceFormat": True,
        "formatSchema": "n: number\nz: number\nhundred: number\nflag: number",
        "formatExample": "n: 3\nz: 0\nhundred: 100\nflag: 0",
    },
    {
        "id": "PrDSubj00",
        "name": "Subjects",
        "description": "Map of records that scripts create and read.",
        "positionInList": 1,
        "dataType": "yaml",
        "variableName": "subjects",
        "visibility": "everyone",
        "updateInstructions": "Never modify this item. Only scripts change it.",
        "initialValue": "amanda:\n  suspicion: 1",
        "initialValueBasedOnPC": "same",
        "autoUpdate": False,
        "enforceFormat": False,
        "formatSchema": "",
        "formatExample": "amanda:\n  suspicion: 1",
    },
    {
        "id": "PrDRes000",
        "name": "Results",
        "description": "One marker per probe cell; PENDING until a script writes it.",
        "positionInList": 2,
        "dataType": "yaml",
        "variableName": "results",
        "visibility": "everyone",
        "updateInstructions": "Never modify this item. Only scripts change it.",
        "initialValue": "\n".join(f'{m}: "PENDING"' for m in MARKERS),
        "initialValueBasedOnPC": "same",
        "autoUpdate": False,
        "enforceFormat": False,
        "formatSchema": "",
        "formatExample": "",
    },
]


def cond(type_, data):
    return {"id": str(uuid.uuid4()), "category": "condition", "type": type_, "data": data}


def script(text):
    return {"id": str(uuid.uuid4()), "type": "effectRunScript", "data": text}


def msg(text):
    return {"id": str(uuid.uuid4()), "type": "effectShowMessage", "data": text}


def mark(m):
    return script(f'$results.{m} = "FIRED"')


def paw(expr):
    return cond("triggerOnPawScript", expr)


def chance(formula):
    return cond("triggerOnRandomChance", formula)


def gate():
    return cond("triggerOnPawScript", GATE["data"])


def prereq(tid):
    return cond("triggerPrereqs", {"prereqs": [tid], "firedThisTurn": False})


def trig(id_, name, conds, effects, **flags):
    t = {"id": id_, "name": name}
    if conds is not None:
        t["triggerConditions"] = conds
    t["triggerEffects"] = effects
    t.update(flags)
    return t


w["triggerEvents"] = [
    trig(
        "PrDSOG01a",
        "Q2 SoG no conditions",
        [],
        [mark("sog_empty"), msg("PROBE SOG-EMPTY")],
        triggerOnStartOfGame=True,
    ),
    trig(
        "PrDSOG02a",
        "Q2 SoG gated control",
        [gate()],
        [mark("sog_gated"), msg("PROBE SOG-GATED")],
        triggerOnStartOfGame=True,
    ),
    # Q10 was NOT run: the absent-key variant was swapped for `[]` while bisecting an editor
    # failure that turned out to be the tracked items lacking `description` (see
    # PLATFORM_BEHAVIOR_NOTES.md). `[]` re-confirms the conditionless-trigger result only.
    trig(
        "PrDABS03a",
        "Q10 triggerConditions empty array (absent key breaks the editor)",
        [],
        [mark("abs_key")],
    ),
    trig(
        "PrDOR04a",
        "Q3 or two valid branches",
        [paw("$probe.z > 2 or $probe.n > 2")],
        [mark("or_valid")],
    ),
    trig(
        "PrDOR05a",
        "Q3b or missing path on right",
        [paw("$probe.n > 2 or $subjects.ghost.suspicion > 0")],
        [mark("or_missing_right")],
    ),
    trig("PrDAND06a", "Q3c and", [paw("$probe.n > 2 and $probe.z < 1")], [mark("and_valid")]),
    trig("PrDIF07a", "Q4 chance if()", [chance("if($probe.n > 2, 100, 0)")], [mark("chance_if")]),
    trig(
        "PrDBAR08a",
        "P15b chance bare handle 100",
        [chance("$probe.hundred")],
        [mark("chance_bare_100")],
    ),
    trig(
        "PrDBAR09a",
        "P15c chance bare handle 0 (expect PENDING)",
        [chance("$probe.z")],
        [mark("chance_bare_0")],
    ),
    trig("PrDADD10a", "chance additive", [chance("$probe.n + 97")], [mark("chance_additive")]),
    trig(
        "PrDTRN11a",
        "P15d chance $game.turn_number*100",
        [chance("$game.turn_number * 100")],
        [mark("chance_game_turn")],
    ),
    trig(
        "PrDTRN12a",
        "chance bare turn_number*100",
        [chance("turn_number * 100")],
        [mark("chance_bare_turn")],
    ),
    trig("PrDPRD13a", "Q5 producer sets flag", [gate()], [script("$probe.flag = 1")]),
    trig(
        "PrDCND14a",
        "Q5 consumer condition reads flag",
        [paw("$probe.flag > 0")],
        [mark("cond_same_turn")],
    ),
    trig(
        "PrDCNS15a",
        "Q6 consumer before producer",
        [gate()],
        [script('$results.order_keys = $subjects.keys().join(",")')],
        canTriggerMoreThanOnce=True,
    ),
    trig(
        "PrDPRD16a",
        "Q6 producer creates late",
        [gate()],
        [script('$subjects.late.suspicion = 1\n$results.late_created = "FIRED"')],
    ),
    trig(
        "PrDERR17a",
        "Q7 errored one-shot",
        [gate()],
        [script('set $x = $subjects.ghost.suspicion\n$results.err_ran = "FIRED"')],
    ),
    trig(
        "PrDPRQ18a",
        "Q7 prereq on errored trigger",
        [gate(), prereq("PrDERR17a")],
        [mark("prereq_after_error")],
    ),
    trig(
        "PrDPRQ19a",
        "Q7 prereq on succeeding trigger",
        [gate(), prereq("PrDPRD16a")],
        [mark("prereq_after_ok")],
    ),
    trig(
        "PrDDEP20a",
        "Q8a two missing levels",
        [gate()],
        [script('$subjects.deep.stats.trust = 1\n$results.deep_create = "FIRED"')],
    ),
    trig(
        "PrDDYN21a",
        "Q8b runtime key",
        [gate()],
        [script('set $k = "dyn"\n$subjects.item($k).suspicion = 1\n$results.dyn_create = "FIRED"')],
    ),
]

OUT.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {OUT} with {len(w['triggerEvents'])} triggers, {len(MARKERS)} markers")
