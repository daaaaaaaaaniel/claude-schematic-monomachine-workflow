#!/usr/bin/env python3
"""Step 1 of placement (d, 2026-10-06): every part beside its board, in its function group (design/groups.py).

Writes out/stage-groups.json: the placements (KiCad mm), one box per group with its label, and each group's area
budget. tools/konnect_stage.py applies it to the live board through Konnect. Nothing goes onto a board here.

Area budget: the sum of the group's courtyards (the area the parts themselves cover), and that times ROUTING, an
allowance for the traces between them on a 2-layer board. Through-hole connectors and the Seed3 count at 1x:
little routes underneath them except their own pins.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import groups as G  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
ROUTING = 2.5          # routing allowance on a 2-layer board for SMD groups (rule of thumb, not a measurement)
GAP = 1.5              # between parts in a cluster
ROW_W = 34.0           # cluster width before wrapping
COL_H = 125.0          # column height before starting a new column of clusters
MAIN_BOX = (180.4, 64.0, 250.4, 164.0)       # KiCad mm (pcb_skeleton: panel + MAIN_OFFSET)
CONTROL_BOX = (100.4, 60.75, 170.4, 167.75)  # panel + CONTROL_OFFSET
THROUGH_HOLE_1X = ("A1", "J13", "J14", "JB1", "JB2", "JB3", "JA1", "JA2", "JA3")


def cluster(refs, fp_of, size, row_w=ROW_W):
    """Shelf-pack the parts (primary first) into a block; returns ({ref: (cx, cy)} relative to the block's top-left,
    width, height)."""
    pos, x, y, row_h, w = {}, 0.0, 0.0, 0.0, 0.0
    for r in refs:
        pw, ph = size[fp_of[r]][:2]
        if x > 0 and x + pw > row_w:
            x, y, row_h = 0.0, y + row_h + GAP, 0.0
        pos[r] = (x + pw / 2, y + ph / 2)
        x += pw + GAP
        row_h = max(row_h, ph)
        w = max(w, x - GAP)
    return pos, w, y + row_h


def main():
    comps = json.load(open(sys.argv[1]))["components"]
    size = json.load(open(sys.argv[2]))
    fp_of = {c["reference"]: c["footprint"] for c in comps}
    out = {"placements": [], "boxes": [], "budget": []}

    def lay(groups, x0, y0, direction):
        x, y, col_w = x0, y0, 0.0
        for name, (prim, rest) in groups.items():
            refs = [prim] + rest
            pos, w, h = cluster(refs, fp_of, size, 72.0 if name == "panel" else ROW_W)
            if y + h + 6 > y0 + COL_H and y > y0:
                x, y, col_w = x + direction * (col_w + 8), y0, 0.0
            bx = x if direction > 0 else x - w
            for r in refs:
                cx, cy = pos[r]
                _, _, ox, oy = size[fp_of[r]]      # courtyard centre relative to the footprint origin
                out["placements"].append({"reference": r, "x": round(bx + cx - ox, 3),
                                          "y": round(y + 4 + cy - oy, 3), "rotation": 0})
            parts = sum(size[fp_of[r]][0] * size[fp_of[r]][1] for r in refs)
            smd = sum(size[fp_of[r]][0] * size[fp_of[r]][1] for r in refs if r not in THROUGH_HOLE_1X)
            out["boxes"].append({"group": name, "primary": prim, "n": len(refs), "x0": bx, "y0": y, "w": w, "h": h + 4})
            out["budget"].append({"group": name, "board": "main" if direction > 0 else "control", "parts": len(refs), "courtyard_mm2": round(parts),
                                  "with_routing_mm2": round(parts - smd + smd * ROUTING)})
            y += h + 10
            col_w = max(col_w, w)

    main_groups = dict(G.MAIN)
    control_groups = dict(G.CONTROL)
    lay(main_groups, MAIN_BOX[2] + 12, MAIN_BOX[1], +1)
    lay(control_groups, CONTROL_BOX[0] - 12, CONTROL_BOX[1], -1)
    json.dump(out, open(os.path.join(OUT, "stage-groups.json"), "w"), indent=1)
    for b in out["budget"]:
        print(b)


if __name__ == "__main__":
    main()
