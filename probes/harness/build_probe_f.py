"""Build Probe F (PawScript view switch inside an extra instruction block) from Probe E.

    python build_probe_f.py <probe-e-imported-2.json> <out.json>

One question: does an extra instruction block whose content is a PawScript expression
re-render from *live* tracked-item values when each turn's prompt is built? If it does,
a player edit to a tracked item between turns reaches the AI on the very next turn —
sidestepping the one-turn lag every trigger-driven instruction change carries (effects
run at step 9 of the lifecycle, after the AI has already written the turn).

Cells:

* ``View A`` / ``View B`` — text items, ``hidden`` (the AI cannot read them directly, so
  the only route into the prompt is the expression), ``autoUpdate: false``, never changed.
  Each holds one unmistakable rule: end every outcome with PINEAPPLE (A) / WALRUS (B).
* ``View Mode`` — text item, ``everyone``, ``autoUpdate: false``, initial ``"A"``. Only the
  player changes it, through the in-game tracked-item editor.
* ``View Instructions`` — the one extra instruction block. Its content is a ``choose`` over
  ``$view_mode`` returning ``$view_a`` or ``$view_b``, plus a plain ``<<view_mode>>`` echo.

No triggers at all, so nothing else can move any value.
"""

from __future__ import annotations

import json
import sys

VIEW_A = (
    "PROBE RULE A: End every outcome with the single capitalised word PINEAPPLE as its "
    "final word. Never mention walruses."
)
VIEW_B = (
    "PROBE RULE B: End every outcome with the single capitalised word WALRUS as its "
    "final word. Never mention pineapples."
)
EIB_CONTENT = (
    "Current view mode: <<view_mode>>.\n"
    '<<choose($view_mode, "A", $view_a, "B", $view_b, "VIEW MODE UNRECOGNISED")>>'
)


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

    world["title"] = "SCHEMA PROBE F - PawScript view switch in instruction block"
    world["description"] = (
        "Probe world: does an extra instruction block built from a PawScript expression "
        "pick up a player's tracked-item edit on the very next turn?"
    )
    world["version"] = "1.00"
    world["recommendedAIModel"] = "lynx"
    world["conditions"] = []
    world["triggerEvents"] = []
    world["instructions"] = (
        "This is a schema probe world. Keep every response to one short sentence. Do not "
        "invent events, characters, or scenery. Obey every extra instruction block exactly."
    )
    world["designNotes"] = (
        "SCHEMA PROBE F. Three tracked items (View A / View B hidden and static, View Mode "
        "player-edited) and one extra instruction block whose content is a PawScript choose() "
        "over $view_mode. See probes/README.md in the infinite-worlds-architect repo."
    )

    world["trackedItems"] = [
        tracked_item(
            "PrbFViewA",
            "View A",
            "view_a",
            "PROBE: static rule text for view A. Never changes.",
            positionInList=0,
            visibility="hidden",
            initialValue=VIEW_A,
            updateInstructions="Never change this value.",
        ),
        tracked_item(
            "PrbFViewB",
            "View B",
            "view_b",
            "PROBE: static rule text for view B. Never changes.",
            positionInList=1,
            visibility="hidden",
            initialValue=VIEW_B,
            updateInstructions="Never change this value.",
        ),
        tracked_item(
            "PrbFMode1",
            "View Mode",
            "view_mode",
            "Either A or B. Only the player changes this, via the tracked-item editor.",
            positionInList=2,
            visibility="everyone",
            initialValue="A",
            updateInstructions="Never change this value. Only the player edits it.",
        ),
    ]

    for pc in world["possibleCharacters"]:
        pc["initialTrackedItemValues"] = []

    world["enableAISpecificInstructionBlocks"] = False
    world["instructionBlocks"] = [
        {"id": "PrbFVwIns", "name": "View Instructions", "content": EIB_CONTENT},
    ]

    with open(out_path, "w") as f:
        json.dump(world, f, indent=2)
        f.write("\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
