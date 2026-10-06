#!/usr/bin/env python3
"""Put a computed placement (auto_place.py JSON) on the live board through Konnect, then check every pad.

    python3 pcb/tools/apply_placement.py out/auto-place-main.json

Flips each part to the JSON's side first (Konnect flip_component, KiCad's own top-to-bottom flip), then sets all
positions and rotations in one call (set_component_placements), saves, and compares every pad on the saved board
with the pad positions the placer computed. Any pad more than 0.01 mm off is reported and the exit code is 1.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from konnect_call import Client  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))


def main():
    data = json.load(open(sys.argv[1]))
    layer = "B.Cu" if data.get("side", "back") == "back" else "F.Cu"
    pl = data["placements"]
    c = Client()
    try:
        got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
        for r in pl:
            if got[r]["layer"] != layer:
                c.call("flip_component", {"board": BOARD, "reference": r, "layer": layer})
        c.call("set_component_placements", {"board": BOARD, "placements": [
            {"reference": r, "x": p["x"], "y": p["y"], "rotation": p["rot"]} for r, p in pl.items()]})
        c.call("save_project", {})
    finally:
        c.close()
    import pcbnew
    b = pcbnew.LoadBoard(BOARD)
    bad = []
    for r, p in pl.items():
        f = b.FindFootprintByReference(r)
        pads = {}
        for q in f.Pads():
            pads.setdefault(q.GetNumber(), []).append((pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y)))
        for num, x, y in p["pads"]:
            if not any(abs(x - a) < 0.01 and abs(y - b_) < 0.01 for a, b_ in pads.get(num, [])):
                bad.append(f"{r} pad {num}: expected ({x}, {y}), board has {pads.get(num)}")
    print(f"{len(pl)} parts placed; pads checked: {'all where computed' if not bad else str(len(bad)) + ' off'}")
    for x in bad[:20]:
        print("  ", x)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
