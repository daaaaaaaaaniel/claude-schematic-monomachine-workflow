#!/usr/bin/env python3
"""Automatic placement of the remaining parts at their function (pcb-layout-review: placement freeze).

    python3 pcb/tools/auto_place.py main  [--refs R1,R2] [-o out.json]    # compute only (reads the saved board)
    python3 pcb/tools/auto_place.py control ...
    python3 pcb/tools/auto_place.py control --free R71,R72  # re-place parts already on the board
    python3 pcb/tools/apply_placement.py out.json                          # put it on the live board (Konnect)

Computed offline with KiCad's pcbnew module on the saved board; nothing is written to the board here.

Each part goes where the pads it connects to already are: the cost of a pose is the orthogonal (|dx| + |dy|)
distance from each of its pads to the nearest placed pad of the same net (signals x1, supplies x0.3, ground x0: the
ground fill reaches it). Through an unplaced two-pad part the net's other side counts at half weight. Parts are taken
in order of how strongly they are tied to what's already placed, then every part is re-placed twice with all the
others fixed. A pose is legal when (rules from d, 2026-10-06/07, docs/placement-workflow.md):
  - its courtyard keeps 0.5 mm from every other courtyard on the same side and 1.5 mm inside the board edge;
  - its pads keep 0.3 mm from other nets' pads, tracks and vias on its copper (through-hole pads: both layers);
    hand-soldered pads keep 1.25 mm (control-board through-hole pads from other pads; anything from the
    board-to-board header pads), d 2026-10-07;
  - its through-hole pads stay out of the other side's courtyards (a jack or pot body sits on them), and no other
    part's through-hole lead sits under its body.
Sides: main board = back (JLC assembly); control board = back (bodies), leads through to the front.
"""
import json
import math
import os
import re
import sys

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import pcbnew  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
AREA = {"main": (180.4, 64.0, 250.4, 164.0), "control": (100.4, 60.75, 170.4, 167.75)}   # Edge.Cuts, KiCad mm
OFFSET = {"main": (180.0, 50.0), "control": (100.0, 50.0)}
GAP = 0.5            # courtyard to courtyard
EDGE = 1.5           # courtyard to board edge
CLEAR = 0.3          # pad to other-net copper
SOLDER = 1.25        # hand soldering: pad to pad on the control board, and to the board-to-board headers (d)
POWER = {"+12V", "-12V", "+3V3_A", "+3V3_D", "VIN", "CTL_+12V", "CTL_-12V", "CTL_+3V3_A"}
GROUND = {"GND", "CTL_GND"}
STEP = 0.25
RADIUS = 14.0
MM = 1e6


def mm(v):
    return v / MM


def which_board(x, y):
    for k, (x0, y0, x1, y1) in AREA.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return k
    return None


def weight(net):
    if not net or net in GROUND or net.startswith("unconnected"):
        return 0.0
    return 0.3 if net in POWER else 1.0


class Shape:
    """A footprint's courtyard box and pads relative to its position, for one rotation on one side."""

    def __init__(self, fp, rot, back):
        f = pcbnew.FOOTPRINT(fp)
        if (f.GetLayer() == pcbnew.B_Cu) != back:
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(rot)
        f.SetPosition(pcbnew.VECTOR2I(0, 0))
        cy = None
        for it in f.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                bb = it.GetBoundingBox()
                r = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
                cy = r if cy is None else (min(cy[0], r[0]), min(cy[1], r[1]), max(cy[2], r[2]), max(cy[3], r[3]))
        if cy is None:
            bb = f.GetBoundingBox(False)
            cy = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
        self.cy = cy
        self.pads = []        # (number, net, x, y, half w, half h, through-hole)
        for p in f.Pads():
            bb = p.GetBoundingBox()
            tht = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            self.pads.append((p.GetNumber(), p.GetNetname(), mm(p.GetPosition().x), mm(p.GetPosition().y),
                              mm(bb.GetWidth()) / 2, mm(bb.GetHeight()) / 2, tht))
        self.rot, self.back = rot, back


class World:
    def __init__(self, path, board):
        self.b = pcbnew.LoadBoard(path)
        self.board = board
        self.fps = {f.GetReference(): f for f in self.b.GetFootprints()}
        self.placed = {}          # ref -> (x, y, Shape) for parts on this board
        for r, f in self.fps.items():
            x, y = mm(f.GetPosition().x), mm(f.GetPosition().y)
            if which_board(x, y) == board:
                self.placed[r] = (x, y, Shape(f, f.GetOrientationDegrees(), f.GetLayer() == pcbnew.B_Cu))
        self.copper = {"F": [], "B": []}  # (geometry, net)
        x0, y0, x1, y1 = AREA[board]
        for t in self.b.GetTracks():
            sx, sy = mm(t.GetStart().x), mm(t.GetStart().y)
            if not (x0 <= sx <= x1 and y0 <= sy <= y1):
                continue
            if t.GetClass() == "PCB_VIA":
                g = Point(sx, sy).buffer(mm(t.GetWidth(pcbnew.F_Cu)) / 2)
                for s in "FB":
                    self.copper[s].append((g, t.GetNetname()))
            else:
                g = LineString([(sx, sy), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2)
                self.copper["F" if t.GetLayer() == pcbnew.F_Cu else "B"].append((g, t.GetNetname()))
        self.shapes = {}
        self.rebuild()

    def shape(self, ref, rot, back):
        k = (ref, rot, back)
        if k not in self.shapes:
            self.shapes[k] = Shape(self.fps[ref], rot, back)
        return self.shapes[k]

    def rebuild(self):
        """Obstacle indexes and net anchors from everything placed."""
        cy = {"F": [], "B": []}
        cu = {"F": [(g, n, "") for g, n in self.copper["F"]], "B": [(g, n, "") for g, n in self.copper["B"]]}
        self.anchor = {}
        for r, (x, y, s) in self.placed.items():
            side = "B" if s.back else "F"
            c = s.cy
            cy[side].append((box(x + c[0], y + c[1], x + c[2], y + c[3]), r))
            for num, net, px, py, hw, hh, tht in s.pads:
                g = box(x + px - hw, y + py - hh, x + px + hw, y + py + hh)
                for sd in ("FB" if tht else side):
                    cu[sd].append((g, net, r))
                if net:
                    self.anchor.setdefault(net, []).append((x + px, y + py, r))
        tht = [(box(x + px - hw, y + py - hh, x + px + hw, y + py + hh), r)
               for r, (x, y, s) in self.placed.items() for num, net, px, py, hw, hh, th in s.pads if th]
        self.tht = (STRtree([g for g, _ in tht]) if tht else None, tht)
        self.cy = {s: (STRtree([g for g, _ in v]) if v else None, v) for s, v in cy.items()}
        self.cu = {s: (STRtree([it[0] for it in v]) if v else None, v) for s, v in cu.items()}

    def legal(self, ref, x, y, s):
        side, other = ("B", "F") if s.back else ("F", "B")
        c = s.cy
        x0, y0, x1, y1 = AREA[self.board]
        if x + c[0] < x0 + EDGE or y + c[1] < y0 + EDGE or x + c[2] > x1 - EDGE or y + c[3] > y1 - EDGE:
            return False
        me = box(x + c[0] - GAP, y + c[1] - GAP, x + c[2] + GAP, y + c[3] + GAP)
        tree, items = self.cy[side]
        if tree is not None:
            for i in tree.query(me, predicate="intersects"):
                if items[i][1] != ref:
                    return False
        tree, items = self.tht                       # no other part's lead under this part's body
        if tree is not None:
            for i in tree.query(box(x + c[0], y + c[1], x + c[2], y + c[3]), predicate="intersects"):
                if items[i][1] != ref:
                    return False
        for num, net, px, py, hw, hh, tht in s.pads:
            pad = box(x + px - hw, y + py - hh, x + px + hw, y + py + hh)
            g = pad.buffer(SOLDER, join_style=2)
            for sd in ("FB" if tht else side):
                tree, items = self.cu[sd]
                if tree is not None:
                    for i in tree.query(g, predicate="intersects"):
                        geom, n2, r2 = items[i]
                        if r2 == ref:
                            continue
                        # hand-soldered pads (control board through-hole, the board-to-board headers) keep
                        # SOLDER from other pads; everything else CLEAR
                        need = SOLDER if r2 and ((tht and self.board == "control") or r2.startswith(("JA", "JB"))) \
                            else CLEAR
                        if (n2 != net or not net) and pad.distance(geom) < need:
                            return False
            if tht:
                tree, items = self.cy[other]
                if tree is not None and len(tree.query(Point(x + px, y + py).buffer(hw), predicate="intersects")):
                    return False
        return True

    def targets(self, ref, net, depth=0):
        """Placed pads of `net` (not on `ref`); through an unplaced 2-pad part, its other net at half weight."""
        pts = [(ax, ay, 1.0) for ax, ay, r in self.anchor.get(net, []) if r != ref]
        if pts or depth:
            return pts
        for r2, f in self.fps.items():
            if r2 == ref or r2 in self.placed or len(f.Pads()) != 2:
                continue
            nets = [p.GetNetname() for p in f.Pads()]
            if net in nets:
                o = nets[1 - nets.index(net)]
                if weight(o) > 0:
                    pts += [(ax, ay, 0.5) for ax, ay, _ in self.targets(ref, o, 1)]
        return pts

    def best(self, ref, back):
        for radius in (RADIUS, 2 * RADIUS, 4 * RADIUS):
            got = self._best(ref, back, radius)
            if got is not None:
                return got
        return None

    def _best(self, ref, back, radius):
        fp = self.fps[ref]
        nets = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
        tg = {n: self.targets(ref, n) for n in set(nets.values()) if weight(n) > 0}
        tg = {n: np.array(v) for n, v in tg.items() if v}
        if not tg:
            return None
        cx = np.mean([v[:, 0].mean() for v in tg.values()])
        cyy = np.mean([v[:, 1].mean() for v in tg.values()])
        g = np.arange(-radius, radius + 1e-9, STEP if radius <= RADIUS else 2 * STEP)
        X, Y = np.meshgrid(cx + g, cyy + g)
        X, Y = X.ravel(), Y.ravel()
        cands = []
        for rot in (0, 90, 180, 270):
            s = self.shape(ref, rot, back)
            cost = np.zeros_like(X)
            for num, net, px, py, hw, hh, tht in s.pads:
                if net not in tg:
                    continue
                t = tg[net]
                d = (np.abs((X + px)[:, None] - t[None, :, 0]) + np.abs((Y + py)[:, None] - t[None, :, 1])) / t[None, :, 2]
                cost += weight(net) * d.min(axis=1)
            for i in np.argsort(cost):
                cands.append((cost[i], X[i], Y[i], rot))
        cands.sort(key=lambda c: (round(c[0], 3), c[3] % 180, math.hypot(c[1] - cx, c[2] - cyy)))
        for c, x, y, rot in cands:
            s = self.shape(ref, rot, back)
            x, y = round(x / STEP) * STEP, round(y / STEP) * STEP
            if self.legal(ref, x, y, s):
                return (c, x, y, rot, s)
        return None


def ties(w, ref):
    f = w.fps[ref]
    return sum(weight(p.GetNetname()) for p in f.Pads()
               if any(r != ref for _, _, r in w.anchor.get(p.GetNetname(), [])))


def main():
    board = sys.argv[1]
    args = sys.argv[2:]
    path = args[args.index("--board") + 1] if "--board" in args else BOARD
    out = args[args.index("-o") + 1] if "-o" in args else os.path.join(HERE, "..", "out", f"auto-place-{board}.json")
    w = World(path, board)
    if "--free" in args:                                  # re-place these: treat them as not yet placed
        for r in args[args.index("--free") + 1].split(","):
            w.placed.pop(r, None)
        w.rebuild()
    if "--refs" in args:
        todo = args[args.index("--refs") + 1].split(",")
    else:
        import groups as G
        table = G.MAIN if board == "main" else G.CONTROL
        todo = [r for prim, rest in table.values() for r in [prim] + list(rest)
                if r in w.fps and r not in w.placed and re.fullmatch(r"(R|C|U)\d+", r)]
    back = True
    result = {}
    left = list(todo)
    while left:
        left.sort(key=lambda r: -ties(w, r))
        ref = left.pop(0)
        got = w.best(ref, back)
        if got is None:
            print(f"{ref}: no legal spot found near its nets", file=sys.stderr)
            continue
        c, x, y, rot, s = got
        w.placed[ref] = (x, y, s)
        w.rebuild()
        result[ref] = (x, y, rot)
    for rnd in range(2):                                  # re-place each with the others fixed
        moved = 0
        for ref in list(result):
            x0, y0, s0 = w.placed.pop(ref)
            w.rebuild()
            got = w.best(ref, back)
            if got and (got[1], got[2], got[3]) != (x0, y0, s0.rot):
                w.placed[ref] = (got[1], got[2], got[4])
                result[ref] = (got[1], got[2], got[3])
                moved += 1
            else:
                w.placed[ref] = (x0, y0, s0)
            w.rebuild()
        print(f"refine pass {rnd + 1}: {moved} moved", file=sys.stderr)
    total = 0.0
    for ref, (x, y, rot) in result.items():
        s = w.placed[ref][2]
        for num, net, px, py, hw, hh, tht in s.pads:
            t = [(ax, ay) for ax, ay, r in w.anchor.get(net, []) if r != ref]
            if t and weight(net):
                total += weight(net) * min(abs(x + px - ax) + abs(y + py - ay) for ax, ay in t)
    print(f"{len(result)} placed, {len(todo) - len(result)} not; weighted pad-to-net distance {total:.0f} mm",
          file=sys.stderr)
    ox, oy = OFFSET[board]
    json.dump({"board": board, "side": "back",
               "placements": {r: {"x": round(x, 4), "y": round(y, 4), "rot": rot,
                                  "pads": [[p[0], round(x + p[2], 4), round(y + p[3], 4)] for p in w.placed[r][2].pads]}
                              for r, (x, y, rot) in result.items()}},
              open(out, "w"), indent=1)
    print(f"written {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
