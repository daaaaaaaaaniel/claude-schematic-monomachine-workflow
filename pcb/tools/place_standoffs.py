#!/usr/bin/env python3
"""Place the optional M3 standoffs (groups.STANDOFFS, d: optional): one pair per corner of the stack.

    python3 pcb/tools/place_standoffs.py [--write]

Each pair is H(n) on the main board and H(n+10) on the control board at the same panel position. A site is legal
when a 3.5 mm radius around the hole (an M3 spacer or nut, about 6.4 mm across corners) is clear of every pad,
track, via and courtyard on both layers of both boards, and the hole sits at least 3.5 mm inside both outlines.
For each corner, the legal site nearest that corner of the shared area is taken. --write applies them through
Konnect (set_component_placements) and saves.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
from shapely.geometry import LineString, Point, Polygon, box  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
OFFSET = {"main": (180.0, 50.0), "control": (100.0, 50.0)}
AREA = {"main": (180.4, 64.0, 250.4, 164.0), "control": (100.4, 60.75, 170.4, 167.75)}
KEEP = 3.5
PAIRS = [("H1", "H11"), ("H2", "H12"), ("H3", "H13"), ("H4", "H14")]


def mm(v):
    return v / 1e6


def board_of(x, y):
    for k, (x0, y0, x1, y1) in AREA.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return k
    return None


def obstacles(b):
    obs = {"main": [], "control": []}
    for f in b.GetFootprints():
        if f.GetReference().startswith("H"):
            continue
        bd = board_of(mm(f.GetPosition().x), mm(f.GetPosition().y))
        if not bd:
            continue
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            ps = f.GetCourtyard(layer)
            if ps.OutlineCount():
                o = ps.Outline(0)
                pts = [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]
                if len(pts) >= 3:
                    obs[bd].append(Polygon(pts).buffer(0))
        for p in f.Pads():
            bb = p.GetBoundingBox()
            obs[bd].append(box(mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())))
    for t in b.GetTracks():
        sx, sy = mm(t.GetStart().x), mm(t.GetStart().y)
        bd = board_of(sx, sy)
        if bd:
            obs[bd].append(Point(sx, sy).buffer(0.5) if t.GetClass() == "PCB_VIA" else
                           LineString([(sx, sy), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2))
    return {k: STRtree(v) for k, v in obs.items()}


def main():
    b = pcbnew.LoadBoard(BOARD)
    trees = obstacles(b)
    x0 = max(AREA[k][0] - OFFSET[k][0] for k in AREA) + KEEP
    x1 = min(AREA[k][2] - OFFSET[k][0] for k in AREA) - KEEP
    y0 = max(AREA[k][1] - OFFSET[k][1] for k in AREA) + KEEP
    y1 = min(AREA[k][3] - OFFSET[k][1] for k in AREA) - KEEP
    legal = []
    for x in np.arange(x0, x1 + 1e-6, 0.5):
        for y in np.arange(y0, y1 + 1e-6, 0.5):
            if all(not len(trees[k].query(Point(x + OFFSET[k][0], y + OFFSET[k][1]).buffer(KEEP),
                                          predicate="intersects")) for k in AREA):
                legal.append((round(float(x), 2), round(float(y), 2)))
    print(f"{len(legal)} legal standoff sites")
    chosen = []
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        cands = [p for p in legal if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) > 20 for q in chosen)]
        if not cands:
            print(f"  corner ({cx:.1f}, {cy:.1f}): no legal site")
            chosen.append(None)
            continue
        p = min(cands, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
        chosen.append(p)
        print(f"  corner ({cx:.1f}, {cy:.1f}): panel {p}, {abs(p[0] - cx) + abs(p[1] - cy):.1f} mm from the corner")
    if "--write" in sys.argv:
        from konnect_call import Client
        moves = []
        for (hm, hc), p in zip(PAIRS, chosen):
            if p is None:
                continue
            moves.append({"reference": hm, "x": p[0] + OFFSET["main"][0], "y": p[1] + OFFSET["main"][1], "rotation": 0})
            moves.append({"reference": hc, "x": p[0] + OFFSET["control"][0], "y": p[1] + OFFSET["control"][1],
                          "rotation": 0})
        c = Client()
        try:
            c.call("set_component_placements", {"board": BOARD, "placements": moves})
            c.call("save_project", {})
        finally:
            c.close()
        print(f"placed {len(moves)} holes")


if __name__ == "__main__":
    main()
