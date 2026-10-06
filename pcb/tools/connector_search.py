#!/usr/bin/env python3
"""Find the board-to-board connectors: up to 4 straight header lines, their pins, and their pin order.

    python3 pcb/tools/connector_search.py [--seed N] [--restarts K] [--free R1,C2,...] [--write]

--free leaves those parts out (as if not yet placed): use it for parts that get re-placed around the connectors.

Rules (d, 2026-10-07; docs/placement-workflow.md section 4):
  - at most 4 lines; each line is one 1xN header pair (2-40 pins), horizontal or vertical, JAn on the control
    board's back over JBn on the main board's front, pin k on pin k; lines may sit right at the board edge;
  - grounds: every connector has at least one; every audio or CV signal has a ground beside it; a supply pin has grounds on both sides; two kinds of
    signal (audio, CV, pot, digital, supply) never sit side by side without a ground between them.
Hand soldering (d, 2026-10-07): every header pad keeps 1.25 mm (edge to edge) from every other part's pad on both
boards, and keeps 1.25 mm from the whole box around each jack, pot and LED on the control front (iron access).
A pin site is legal when, at the same panel position, on the main board it keeps 0.3 mm from all copper on both
layers and stays out of the back-side courtyards (the Seed3's only along its socket strips: a header between the
socket rows is fine, soldered before the sockets), and on the control board its pad keeps 0.3 mm from all copper,
stays out of the front-side courtyards (jack, pot and LED bodies) and its socket body stays out of the back-side ones.

Cost = orthogonal distance from each signal's pin to the nearest placed pad of that signal on the main board plus to
its CTL_ twin on the control board, + 1 per ground pin + 5 per line (fewer, longer lines are easier to align).
Search: simulated annealing over lines made of "blocks" (an audio or CV block holds 1-2 signals, a supply block
1, pot and digital blocks any number; grounds go between blocks and wherever a rule needs one), several restarts,
best kept. Writes design/pinmap.py HEADER_PINS / HEADER_POS with --write, plus out/connector-search.json.
"""
import json
import math
import os
import random
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import pcbnew  # noqa: E402
from shapely.geometry import LineString, Point, box  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402
import pinmap as PM  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
PINMAP = os.path.join(HERE, "..", "design", "pinmap.py")
OUT = os.path.join(HERE, "..", "out", "connector-search.json")
OFFSET = {"main": (180.0, 50.0), "control": (100.0, 50.0)}
AREA = {"main": (180.4, 64.0, 250.4, 164.0), "control": (100.4, 60.75, 170.4, 167.75)}
LAT = 1.27                      # lattice for pin sites, mm (pins are 2 steps apart)
PITCH = 2
PAD_R = 0.85                    # 1.7 mm pads (pin 1 is square: clearances are taken from the square)
CLEAR = 0.3
SOLDER = 1.25                   # header pad to any other part's pad, edge to edge: hand soldering (d, 2026-10-07)
BODY = 1.27                     # half the header body width
CRT = 1.8                       # half the socket courtyard width (PinSocket_1xNN: 0.5 mm past the body)
SUPPLY = {"+12V", "-12V", "+3V3_A"}
MAX_LINES = 4
W_GND, W_LINE = 1.0, 5.0
BAD = 1e5                       # per illegal pin or clash: far above any real distance


def kind(s):
    if s in SUPPLY:
        return "supply"
    if s.startswith("CV_"):
        return "cv"
    if s.startswith("POT_"):
        return "pot"
    if s in ("IN_L", "IN_R", "OUT_L", "OUT_R"):
        return "audio"
    return "digital"


CAP = {"audio": 2, "cv": 2, "supply": 1, "pot": 9, "digital": 9}
NEEDS_GND = {"audio", "cv"}


def mm(v):
    return v / 1e6


def courtyard(f):
    """The footprint's courtyard as a polygon (its outline, not the box around it); None if it has none."""
    from shapely.geometry import Polygon
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        ps = f.GetCourtyard(layer)
        if ps.OutlineCount():
            o = ps.Outline(0)
            pts = [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]
            if len(pts) >= 3:
                return Polygon(pts).buffer(0)
    return None


def board_of(x, y):
    for k, (x0, y0, x1, y1) in AREA.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return k
    return None


def load(free=()):
    """free: parts to leave out (they get re-placed around the connectors afterwards)."""
    b = pcbnew.LoadBoard(BOARD)
    copper = {"main": [], "control": []}
    cy = {("main", "F"): [], ("main", "B"): [], ("control", "F"): [], ("control", "B"): []}
    socket = []
    targets = {}
    tht = {"main": [], "control": []}
    pads = {"main": [], "control": []}
    for f in b.GetFootprints():
        ref = f.GetReference()
        fx, fy = mm(f.GetPosition().x), mm(f.GetPosition().y)
        bd = board_of(fx, fy)
        if bd is None or ref.startswith(("JA", "JB")) or ref in free:
            continue
        side = "B" if f.GetLayer() == pcbnew.B_Cu else "F"
        if ref != "A1":
            g = courtyard(f)
            if g is not None:
                # control front (jack, pot, LED bodies): the whole box, not a notched outline (hand soldering)
                cy[(bd, side)].append(box(*g.bounds) if (bd, side) == ("control", "F") else g)
        xs = []
        for p in f.Pads():
            bb = p.GetBoundingBox()
            g = box(mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
            copper[bd].append(g)
            pads[bd].append(g)
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                tht[bd].append(g)                             # leads stick out on both sides
            px, py = mm(p.GetPosition().x), mm(p.GetPosition().y)
            targets.setdefault((bd, p.GetNetname()), []).append((px - OFFSET[bd][0], py - OFFSET[bd][1]))
            if ref == "A1":
                xs.append((px, py))
        if ref == "A1":                                   # the Seed3's two socket strips
            for col in {round(x, 2) for x, _ in xs}:
                ys = [y for x, y in xs if round(x, 2) == col]
                socket.append(box(col - 1.27, min(ys) - 1.27, col + 1.27, max(ys) + 1.27))
    for t in b.GetTracks():
        sx, sy = mm(t.GetStart().x), mm(t.GetStart().y)
        bd = board_of(sx, sy)
        if bd is None:
            continue
        if t.GetClass() == "PCB_VIA":
            copper[bd].append(Point(sx, sy).buffer(mm(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            copper[bd].append(LineString([(sx, sy), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2))
    cy[("main", "B")] += socket
    cy[("control", "tht")] = tht["control"]
    cy[("main", "pads")] = pads["main"]
    cy[("control", "pads")] = pads["control"]
    return copper, cy, targets


def legal_grid(copper, cy):
    """Boolean grid over panel lattice points: may a header pin sit here on both boards?"""
    trees = {k: STRtree(v) if v else None for k, v in list(copper.items()) + list(cy.items())}
    x0 = max(AREA["main"][0] - OFFSET["main"][0], AREA["control"][0] - OFFSET["control"][0]) + BODY
    x1 = min(AREA["main"][2] - OFFSET["main"][0], AREA["control"][2] - OFFSET["control"][0]) - BODY
    y0 = max(AREA["main"][1] - OFFSET["main"][1], AREA["control"][1] - OFFSET["control"][1]) + BODY
    y1 = min(AREA["main"][3] - OFFSET["main"][1], AREA["control"][3] - OFFSET["control"][1]) - BODY
    xs = np.arange(math.ceil(x0 / LAT) * LAT, x1 + 1e-6, LAT)
    ys = np.arange(math.ceil(y0 / LAT) * LAT, y1 + 1e-6, LAT)
    ok = np.zeros((len(xs), len(ys)), bool)

    def hits(key, g):
        t = trees[key]
        return t is not None and len(t.query(g, predicate="intersects")) > 0
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            mx, my = x + OFFSET["main"][0], y + OFFSET["main"][1]
            cx, cy_ = x + OFFSET["control"][0], y + OFFSET["control"][1]
            pin_m = Point(mx, my).buffer(PAD_R + CLEAR)
            pin_c = Point(cx, cy_).buffer(PAD_R + CLEAR)
            if hits("main", pin_m) or hits(("main", "B"), Point(mx, my).buffer(PAD_R)) \
                    or hits(("main", "pads"), box(mx - PAD_R, my - PAD_R, mx + PAD_R, my + PAD_R).buffer(SOLDER)):
                continue
            if hits("control", pin_c) or hits(("control", "F"), box(cx - PAD_R, cy_ - PAD_R, cx + PAD_R, cy_ + PAD_R).buffer(SOLDER)) \
                    or hits(("control", "pads"), box(cx - PAD_R, cy_ - PAD_R, cx + PAD_R, cy_ + PAD_R).buffer(SOLDER)):
                continue
            body = box(cx - BODY, cy_ - BODY, cx + BODY, cy_ + BODY)
            crt = box(cx - CRT, cy_ - CRT, cx + CRT, cy_ + CRT)     # the socket's courtyard, as KiCad draws it
            if hits(("control", "B"), crt) or hits(("control", "tht"), body.buffer(CLEAR)):
                continue                              # the socket body sits on the back: no parts, no leads under it
            ok[i, j] = True
    return xs, ys, ok


class Problem:
    def __init__(self, free=()):
        copper, cy, targets = load(free)
        self.xs, self.ys, self.ok = legal_grid(copper, cy)
        self.sigs = [s for pins in PM.HEADER_PINS.values() for s in pins if s != "GND"]
        X, Y = np.meshgrid(self.xs, self.ys, indexing="ij")
        self.cost = {}
        self.missing = []
        for s in self.sigs:
            c = np.zeros_like(X)
            for bd, net in (("main", s), ("control", "CTL_" + s)):
                t = targets.get((bd, net))
                if not t:
                    self.missing.append(f"{net} ({bd})")
                    continue
                t = np.array(t)
                c += np.min(np.abs(X[..., None] - t[:, 0]) + np.abs(Y[..., None] - t[:, 1]), axis=-1)
            self.cost[s] = c
        self.nx, self.ny = self.ok.shape
        self.runs = []                                  # maximal straight runs of legal sites, 2 lattice steps apart
        for o in "hv":
            for fixed in range(self.ny if o == "h" else self.nx):
                for parity in (0, 1):
                    run = []
                    n = self.nx if o == "h" else self.ny
                    for k in list(range(parity, n, PITCH)) + [None]:
                        site = None if k is None else ((k, fixed) if o == "h" else (fixed, k))
                        if site is not None and self.ok[site]:
                            run.append(site)
                        else:
                            if len(run) >= 2:
                                self.runs.append(run)
                            run = []
        self.runs.sort(key=len, reverse=True)

    # a solution: list of lines; line = dict(o="h"|"v", i, j (pin 1 lattice index), dir=+1|-1, blocks=[[sig,...],...])
    @staticmethod
    def tokens(line):
        """The line's pin sequence: signals with the grounds the rules need."""
        out = []
        blocks = [b for b in line["blocks"] if b]
        for n, bl in enumerate(blocks):
            k = kind(bl[0])
            if n == 0 and (k in ("supply",) or (k in NEEDS_GND and len(bl) == 2)):
                out.append("GND")
            if n > 0:
                out.append("GND")
            out += bl
            if n == len(blocks) - 1 and (k == "supply" or (k in NEEDS_GND and len(bl) == 2)):
                out.append("GND")
        if blocks and len(blocks) == 1 and kind(blocks[0][0]) in NEEDS_GND and len(blocks[0]) == 1:
            out.append("GND")                         # a lone audio/CV pin still needs its ground
        if out and "GND" not in out:
            out.append("GND")                         # every connector carries at least one ground
        return out

    def pins(self, line, n):
        run = self.runs[line["run"]]
        sites = run[line["off"]:line["off"] + n]
        return sites[::-1] if line["rev"] else sites

    def score(self, sol):
        total, boxes = 0.0, []
        for line in sol:
            tok = self.tokens(line)
            if not tok:
                continue
            total += W_LINE
            run = self.runs[line["run"]]
            if line["off"] + len(tok) > len(run):
                total += BAD * (line["off"] + len(tok) - len(run))
            pins = self.pins(line, len(tok))
            for (i, j), t in zip(pins, tok):
                total += W_GND if t == "GND" else self.cost[t][i, j]
            i0, i1 = min(p[0] for p in pins), max(p[0] for p in pins)
            j0, j1 = min(p[1] for p in pins), max(p[1] for p in pins)
            for a0, a1, b0, b1 in boxes:                 # bodies of different lines keep apart (>= 3 lattice steps)
                if i0 - 2 <= a1 and a0 <= i1 + 2 and j0 - 2 <= b1 and b0 <= j1 + 2:
                    total += BAD
            boxes.append((i0, i1, j0, j1))
        return total


def new_line(P, rng, blocks=None):
    return dict(run=rng.randrange(len(P.runs)), off=0, rev=rng.random() < 0.5, blocks=blocks or [])


def fit(P, line):
    """Keep the line's offset inside its run where possible."""
    n = len(P.tokens(line))
    line["off"] = max(0, min(line["off"], len(P.runs[line["run"]]) - n))


def random_solution(P, rng):
    by_kind = {}
    for s in P.sigs:
        by_kind.setdefault(kind(s), []).append(s)
    blocks = []
    for k, ss in by_kind.items():
        rng.shuffle(ss)
        cap = CAP[k]
        blocks += [ss[n:n + cap] for n in range(0, len(ss), cap)]
    rng.shuffle(blocks)
    sol = [new_line(P, rng) for _ in range(rng.randint(2, MAX_LINES))]
    for b in blocks:
        rng.choice(sol)["blocks"].append(b)
    for l in sol:
        l["run"] = rng.randrange(min(len(P.runs), 40))
        fit(P, l)
    return [l for l in sol if l["blocks"]]


def mutate(P, sol, rng):
    s = [dict(l, blocks=[list(b) for b in l["blocks"]]) for l in sol]
    m = rng.random()
    if m < 0.20:                                        # slide a line along its run
        l = rng.choice(s)
        l["off"] = max(0, l["off"] + rng.choice((-1, 1)) * rng.choice((1, 1, 2, 4)))
        fit(P, l)
    elif m < 0.32:                                      # move a line to another run (nearby or anywhere)
        l = rng.choice(s)
        n = len(P.tokens(l))
        cands = [k for k, r in enumerate(P.runs) if len(r) >= n]
        if cands:
            l["run"] = rng.choice(cands)
            l["off"] = rng.randrange(len(P.runs[l["run"]]) - n + 1)
    elif m < 0.38:                                      # reverse a line
        rng.choice(s)["rev"] ^= True
    elif m < 0.60:                                      # move a block (to another line, or a new one)
        a = rng.choice(s)
        if not a["blocks"]:
            return s
        bl = a["blocks"].pop(rng.randrange(len(a["blocks"])))
        if len(s) < MAX_LINES and rng.random() < 0.1:
            tgt = new_line(P, rng)
            s.append(tgt)
        else:
            tgt = rng.choice(s)
        tgt["blocks"].insert(rng.randrange(len(tgt["blocks"]) + 1), bl)
        fit(P, tgt)
    elif m < 0.85:                                      # swap two signals of one kind
        flat = [(b, k) for l in s for b in l["blocks"] for k in range(len(b))]
        a = rng.choice(flat)
        same = [x for x in flat if kind(x[0][x[1]]) == kind(a[0][a[1]]) and x is not a]
        if same:
            bb = rng.choice(same)
            a[0][a[1]], bb[0][bb[1]] = bb[0][bb[1]], a[0][a[1]]
    else:                                               # split or merge audio/CV blocks
        flat = [(l, n) for l in s for n, b in enumerate(l["blocks"]) if kind(b[0]) in NEEDS_GND]
        if flat:
            l, n = rng.choice(flat)
            b = l["blocks"][n]
            if len(b) == 2:
                l["blocks"][n:n + 1] = [[b[0]], [b[1]]]
            else:
                for l2 in s:
                    for n2, b2 in enumerate(l2["blocks"]):
                        if b2 is not b and len(b2) == 1 and kind(b2[0]) == kind(b[0]):
                            l["blocks"][n] = b + b2
                            del l2["blocks"][n2]
                            break
                    else:
                        continue
                    break
            for l2 in s:
                fit(P, l2)
    return [l for l in s if l["blocks"]] or s


def anneal(P, rng, iters=120000):
    cur = random_solution(P, rng)
    cs = P.score(cur)
    best, bs = cur, cs
    T0, T1 = 50.0, 0.05
    for k in range(iters):
        T = T0 * (T1 / T0) ** (k / iters)
        nxt = mutate(P, cur, rng)
        ns = P.score(nxt)
        if ns < cs or rng.random() < math.exp((cs - ns) / T):
            cur, cs = nxt, ns
            if cs < bs:
                best, bs = cur, cs
    return best, bs


def rotations():
    """Header rotations that lay pin k along +x, -x, +y, -y: (JB on the front, JA flipped to the back)."""
    b = pcbnew.LoadBoard(BOARD)
    res = {}
    for ref, back in (("JB1", False), ("JA1", True)):
        f = pcbnew.FOOTPRINT(b.FindFootprintByReference(ref))
        if (f.GetLayer() == pcbnew.B_Cu) != back:
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for rot in (0, 90, 180, 270):
            f.SetOrientationDegrees(rot)
            f.SetPosition(pcbnew.VECTOR2I(0, 0))
            p = {q.GetNumber(): (mm(q.GetPosition().x), mm(q.GetPosition().y)) for q in f.Pads()}
            d = (round(p["2"][0] - p["1"][0], 2), round(p["2"][1] - p["1"][1], 2))
            res[(ref[:2], d)] = (rot, p["1"])
    return res


def main():
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 1
    restarts = int(args[args.index("--restarts") + 1]) if "--restarts" in args else 8
    free = args[args.index("--free") + 1].split(",") if "--free" in args else []
    P = Problem(free)
    print(f"legal pin sites: {int(P.ok.sum())} of {P.ok.size} lattice points (both boards)")
    if P.missing:
        print("no placed target for:", ", ".join(P.missing))
    rng = random.Random(seed)
    best, bs = None, float("inf")
    for r in range(restarts):
        sol, s = anneal(P, rng)
        print(f"  restart {r + 1}: score {s:.1f}")
        if s < bs:
            best, bs = sol, s
    if bs >= BAD:
        sys.exit(f"no legal arrangement found (best score {bs:.0f}: {int(bs // BAD)} illegal pins or clashes)")
    rot = rotations()
    lines = []
    for n, line in enumerate(best):
        tok = P.tokens(line)
        if not tok:
            continue
        pins = P.pins(line, len(tok))
        xy = [(round(float(P.xs[i]), 3), round(float(P.ys[j]), 3)) for i, j in pins]
        d = (round(xy[1][0] - xy[0][0], 2), round(xy[1][1] - xy[0][1], 2)) if len(xy) > 1 else (0.0, 2.54)
        rjb, o_jb = rot[("JB", d)]
        rja, o_ja = rot[("JA", d)]
        sig_mm = sum(float(P.cost[t][i, j]) for (i, j), t in zip(pins, tok) if t != "GND")
        lines.append({"pins": tok, "pin1": xy[0], "step": d, "rot_JB": rjb, "rot_JA": rja,
                      "origin_JB": [xy[0][0] - o_jb[0], xy[0][1] - o_jb[1]],
                      "origin_JA": [xy[0][0] - o_ja[0], xy[0][1] - o_ja[1]], "signal_mm": round(sig_mm, 1)})
    lines.sort(key=lambda l: (l["pin1"][1], l["pin1"][0]))
    total_pins = sum(len(l["pins"]) for l in lines)
    print(f"best: {len(lines)} lines, {total_pins} pins "
          f"({sum(l['pins'].count('GND') for l in lines)} ground), signal distance "
          f"{sum(l['signal_mm'] for l in lines):.0f} mm, score {bs:.1f}")
    for n, l in enumerate(lines, 1):
        o = "horizontal" if l["step"][1] == 0 else "vertical"
        print(f"  J{n}: {len(l['pins'])} pins, {o}, pin 1 at panel {l['pin1']}: {', '.join(l['pins'])}")
    json.dump({"score": bs, "lines": lines}, open(OUT, "w"), indent=1)
    if "--write" in args:
        pins = {str(n): l["pins"] for n, l in enumerate(lines, 1)}
        pos = {str(n): (l["pin1"][0], l["pin1"][1], l["rot_JB"], l["rot_JA"]) for n, l in enumerate(lines, 1)}
        t = open(PINMAP).read()
        t = re.sub(r"^HEADER_PINS = .*$", "HEADER_PINS = " + repr(pins), t, count=1, flags=re.M)
        t = re.sub(r"^HEADER_POS = .*$", "HEADER_POS = " + repr(pos) + "   # pin 1 panel x, y; rotation of JBn "
                   "(main, front) and of JAn (control, back), from tools/connector_search.py", t, count=1, flags=re.M)
        open(PINMAP, "w").write(t)
        print("written to design/pinmap.py HEADER_PINS, HEADER_POS; placements in", OUT)


if __name__ == "__main__":
    main()
