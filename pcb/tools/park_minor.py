#!/usr/bin/env python3
"""Move every untraced minor part (d's rule: it doesn't exist until it gets a trace) back to its staged spot beside
its board (out/stage-groups.json), in one undo step. Traced minor parts, secondary parts and primaries stay."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drc_summary as D  # noqa: E402
from konnect_call import Client  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
staged = {p["reference"]: p for p in json.load(open(os.path.join(HERE, "..", "out", "stage-groups.json")))["placements"]}
traced = D.traced_parts()
c = Client()
try:
    on = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
    park = sorted(r for r in staged if r in on and D.re.fullmatch(r"[RC]\d+", r) and r not in D.SECONDARY
                  and r not in traced and 180 <= on[r]["x"] <= 251)          # only those now on the main board
    if park:
        c.call("set_component_placements", {"board": BOARD, "placements": [staged[r] for r in park]})
    print(f"parked {len(park)} untraced minor parts: {' '.join(park)}")
    print("kept (traced):", " ".join(sorted(r for r in traced if D.re.fullmatch(r"[RC]\d+", r))))
    print("save:", c.call("save_project", {}))
finally:
    c.close()
