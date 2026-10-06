"""Board-to-board header search (d, 2026-10-06): three or four single-row 2.54 mm headers, any orientation, any
length. Signal groups are not headers: a header is a row of pins, and a group (audio, CV, pots, ...) is a section of
a row, which can share a row with other sections or be split across rows (d: "one long header could run all the way
from the top of the PCB to the bottom ... one section for the audio pins (near the top), and another for the CV").

  1. Units. The crossing signals are paired within their kind (the two audio inputs, the two outputs, CV with CV, pot wipers together,
     digital selects together; the cheapest pairing by distance), and each supply is a unit of its own. A unit sits
     on a slot of three pins: GND, signal, signal (a supply leaves its second pin as GND). So a GND separates every
     pair, and a switching line never sits next to an analog one.
  2. Rows. Every legal straight run of pin positions, vertical and horizontal: each pin clear of the control board's
     front parts (pins and bodies), the socket's body clear on the control board's back, inside both outlines, and
     every pin at least SEED_MIN from every Seed3 pin (room for an iron between header and Seed socket).
  3. Assignment. For a set of rows, units go to slots by minimum total weighted trace length (Hungarian matching, as
     the floorplan's pin matching). Each row is then trimmed to its used slots; a gap of two or more empty slots
     splits it into two headers.
  4. Choice of rows: greedy (add the row that lowers the cost most), then local search (swap, add or drop a row)
     from several starts. Cost = trace length + HEADER_PENALTY per header + PIN_PENALTY per pin.
The floorplan then alternates: headers for a given Seed3 position, the Seed3 position for those headers, until both
settle.
"""
import itertools
import math
import os

import numpy as np
from scipy.optimize import linear_sum_assignment

from geom import dist

PITCH = 2.54
STEP = 0.635               # site grid; PITCH = 4 * STEP
SEED_MIN = 5.08            # header pin to Seed3 pin, centre to centre (d: hand soldering)
PAD_KEEP = 1.85            # half-size of the keep-clear square round a header pin on the control board's front
BODY_HALF = 1.27 + 0.4     # half-width of a header body plus clearance
BODY_GAP = 1.0             # between two headers' bodies
EDGE = 2.5                 # header pin to board edge
HEADER_PENALTY = 15.0      # weighted mm per header: near-ties go to fewer headers
PIN_PENALTY = 0.5          # weighted mm per pin: no needless length
MIN_HEADERS = int(os.environ.get("HDR_MIN", 3))   # d: three or four headers; five is too many
MAX_HEADERS = int(os.environ.get("HDR_MAX", 4))
GAP_SPLIT = 2              # this many empty slots or more inside a row: two headers
MIN_RUN = 4                # pins
STARTS = 12                # local-search starts
BIG = 1000.0
DIRS = {0: (0.0, 1.0), 90: (1.0, 0.0), 180: (0.0, -1.0), 270: (-1.0, 0.0)}   # pin k = pin 1 + k * PITCH * dir
ROT_BACK = {0: 0, 90: 270, 180: 180, 270: 90}   # the socket on the control board's back that lands pin k on pin k
POWER = ("+12V", "-12V", "+3V3_A")
DIGITAL = ("MUX_A", "MUX_B", "MUX_C", "LED_A")       # switching lines: never paired with an analog one
GROUP_OF = {"IN_L": "audio", "IN_R": "audio", "OUT_L": "audio", "OUT_R": "audio",
            "POT_VOL": "pots", "POT_MUX": "pots", "MUX_A": "digital", "MUX_B": "digital", "MUX_C": "digital",
            "LED_A": "digital", "+12V": "power", "-12V": "power", "+3V3_A": "power"}


def crossing_signals(ctl, sp, cv_names, j13_xy, w):
    """{signal: (control end, main end, weight)}. Main ends are proxies before the op-amps are placed: the codec pins
    for audio, the ADC pins' centre for CV and pots (U1/U2 sit by the ADC pins), the Seed3 GPIO pins for the digital
    lines, the power entry for +/-12 V and the Seed3's 3V3_A pin for +3V3_A."""
    adc = [sp[str(k)] for k in range(22, 33)]
    adc_c = (sum(p[0] for p in adc) / len(adc), sum(p[1] for p in adc) / len(adc))
    f, u6 = ctl["front"], ctl["u6"]
    S = {"IN_L": (ctl["tip"]["IN_L"], sp["16"], w["robust"]), "IN_R": (ctl["tip"]["IN_R"], sp["17"], w["robust"]),
         "OUT_L": (ctl["tip"]["OUT_L"], sp["18"], w["robust"]), "OUT_R": (ctl["tip"]["OUT_R"], sp["19"], w["robust"]),
         "POT_VOL": (f["RV1"]["2"][0][:2], adc_c, w["slow"]), "POT_MUX": (u6["3"][0][:2], adc_c, w["slow"]),
         "MUX_A": (u6["11"][0][:2], sp["8"], w["slow"]), "MUX_B": (u6["10"][0][:2], sp["9"], w["slow"]),
         "MUX_C": (u6["9"][0][:2], sp["10"], w["slow"]), "LED_A": (f["D1"]["2"][0][:2], sp["12"], w["slow"]),
         "+3V3_A": (u6["16"][0][:2], sp["21"], w["slow"]),
         "+12V": ((57.0, 83.5), j13_xy, w["power"]), "-12V": ((57.0, 83.5), j13_xy, w["power"])}
    for n in cv_names:
        S[f"CV_{n}"] = (ctl["tip"][f"CV_{n}"], adc_c, w["robust"])
    return S


def kind(s):
    return "P" if s in POWER else "D" if s in DIGITAL else "A"


def _matchings(items):
    if len(items) < 2:
        yield [tuple(items)] if items else []
        return
    a = items[0]
    for i in range(1, len(items)):
        for rest in _matchings(items[1:i] + items[i + 1:]):
            yield [(a, items[i])] + rest
    if len(items) % 2:                     # odd: a may stay single
        for rest in _matchings(items[1:]):
            yield [(a,)] + rest


def units(S):
    """Pairs within each group (cheapest pairing: control ends and main ends close together), supplies single."""
    groups = {}
    for s in S:
        groups.setdefault(GROUP_OF.get(s, "cv"), []).append(s)
    out = []
    for g, members in sorted(groups.items()):
        if g == "power":
            out += [(s,) for s in members]
            continue
        if g == "audio":                   # inputs together, outputs together: no output beside an input
            out += [("IN_L", "IN_R"), ("OUT_L", "OUT_R")]
            continue
        members = sorted(members)
        best = min((m for m in _matchings(members) if sum(len(u) == 1 for u in m) <= len(members) % 2),
                   key=lambda m: sum(dist(S[u[0]][0], S[u[1]][0]) + dist(S[u[0]][1], S[u[1]][1]) for u in m if len(u) == 2))
        out += best
    return out


class SiteMap:
    """Legal header sites, given the control board (front parts and U6 placed) and the Seed3's pad positions."""

    def __init__(self, cb, seed_pins, outline):
        self.cb = cb
        self.If = cb.integral("front")
        self.Ib = cb.integral("back")
        self.seed = np.array(seed_pins)
        self.x0, self.y0, self.x1, self.y1 = outline

    def sites(self, n, center, radius):
        """All legal (x1, y1, rot) for an n-pin header with its middle within `radius` of `center`, and the pin
        positions as an array (sites, n, 2)."""
        out_xy, out_meta = [], []
        xs = np.arange(self.x0 + EDGE, self.x1 - EDGE + 1e-6, STEP)
        ys = np.arange(self.y0 + EDGE, self.y1 - EDGE + 1e-6, STEP)
        X, Y = np.meshgrid(xs, ys)
        X, Y = X.ravel(), Y.ravel()
        k = np.arange(n) * PITCH
        for rot, (dx, dy) in DIRS.items():
            px = X[:, None] + dx * k[None]
            py = Y[:, None] + dy * k[None]
            mx, my = px.mean(1), py.mean(1)
            ok = np.hypot(mx - center[0], my - center[1]) < radius
            ok &= (px.min(1) >= self.x0 + EDGE) & (px.max(1) <= self.x1 - EDGE)
            ok &= (py.min(1) >= self.y0 + EDGE) & (py.max(1) <= self.y1 - EDGE)
            if not ok.any():
                continue
            px, py, Xo, Yo = px[ok], py[ok], X[ok], Y[ok]
            good = np.ones(len(px), bool)
            for j in range(n):          # every pin clear on the control board's front
                good &= self.cb.box_free(self.If, px[:, j] - PAD_KEEP, py[:, j] - PAD_KEEP,
                                         px[:, j] + PAD_KEEP, py[:, j] + PAD_KEEP)
            good &= self.cb.box_free(self.Ib, px.min(1) - BODY_HALF, py.min(1) - BODY_HALF,   # socket body, back
                                     px.max(1) + BODY_HALF, py.max(1) + BODY_HALF)
            if len(self.seed):
                d = np.hypot(px[..., None] - self.seed[None, None, :, 0], py[..., None] - self.seed[None, None, :, 1])
                good &= d.min(axis=(1, 2)) >= SEED_MIN
            for i in np.nonzero(good)[0]:
                out_xy.append(np.stack([px[i], py[i]], 1))
                out_meta.append((round(float(Xo[i]), 3), round(float(Yo[i]), 3), rot))
        return out_meta, out_xy


    def runs(self):
        """Every maximal straight run of legal pin positions (at least MIN_RUN pins), vertical and horizontal.
        Returns [(rot, pins (n, 2))]; rot 0 = pin 1 at the top, 90 = pin 1 at the left."""
        xs = np.arange(self.x0 + EDGE, self.x1 - EDGE + 1e-6, STEP)
        ys = np.arange(self.y0 + EDGE, self.y1 - EDGE + 1e-6, STEP)
        X, Y = np.meshgrid(xs, ys)                      # [iy, ix]
        out = []
        for rot in (0, 90):
            hx, hy = (BODY_HALF, PITCH / 2) if rot == 0 else (PITCH / 2, BODY_HALF)
            ok = self.cb.box_free(self.If, X - PAD_KEEP, Y - PAD_KEEP, X + PAD_KEEP, Y + PAD_KEEP)
            ok &= self.cb.box_free(self.Ib, X - hx, Y - hy, X + hx, Y + hy)
            if len(self.seed):
                d = np.hypot(X[..., None] - self.seed[None, None, :, 0], Y[..., None] - self.seed[None, None, :, 1])
                ok &= d.min(-1) >= SEED_MIN
            lines = [ok[:, i] for i in range(ok.shape[1])] if rot == 0 else [ok[i, :] for i in range(ok.shape[0])]
            for li, line in enumerate(lines):
                for ph in range(4):
                    idx = np.arange(ph, len(line), 4)
                    seq = line[idx]
                    k = 0
                    while k < len(seq):
                        if not seq[k]:
                            k += 1
                            continue
                        e = k
                        while e < len(seq) and seq[e]:
                            e += 1
                        if e - k >= MIN_RUN:
                            j = idx[k:e]
                            pins = (np.stack([np.full(len(j), xs[li]), ys[j]], 1) if rot == 0
                                    else np.stack([xs[j], np.full(len(j), ys[li])], 1))
                            out.append((rot, pins))
                        k = e
        return out


def _rect(xy):
    xy = np.asarray(xy)
    return (xy[:, 0].min() - BODY_HALF, xy[:, 1].min() - BODY_HALF, xy[:, 0].max() + BODY_HALF, xy[:, 1].max() + BODY_HALF)


def _apart(a, b):
    return a[2] + BODY_GAP <= b[0] or b[2] + BODY_GAP <= a[0] or a[3] + BODY_GAP <= b[1] or b[3] + BODY_GAP <= a[1]


class Run:
    """One candidate row: its slots (pins 3k+1, 3k+2; GND at 3k and 3k+3) and every unit's cost on every slot."""

    def __init__(self, rot, pins, U, S):
        self.rot, self.pins = rot, pins
        self.nslots = (len(pins) - 1) // 3
        n = self.nslots
        p1, p2 = pins[1:3 * n:3], pins[2:3 * n + 1:3]
        def c(s, p):
            a, b, w = S[s]
            return w * (np.hypot(p[:, 0] - a[0], p[:, 1] - a[1]) + np.hypot(p[:, 0] - b[0], p[:, 1] - b[1]))
        self.cost = np.empty((len(U), n))
        self.swap = np.zeros((len(U), n), bool)
        for i, u in enumerate(U):
            if len(u) == 1:
                self.cost[i] = c(u[0], p1)
            else:
                straight, swapped = c(u[0], p1) + c(u[1], p2), c(u[1], p1) + c(u[0], p2)
                self.cost[i] = np.minimum(straight, swapped)
                self.swap[i] = swapped < straight


def evaluate(sel, runs, U, detail=False):
    """Cost of a set of runs (indices): assignment + header and pin penalties. With detail, also the headers."""
    if not sel:
        return math.inf, None
    C = np.hstack([runs[r].cost for r in sel])
    owner = np.concatenate([[(j, k) for k in range(runs[r].nslots)] for j, r in enumerate(sel)])
    rows, cols = linear_sum_assignment(C)
    total = float(C[rows, cols].sum()) + BIG * (len(U) - len(rows))
    used = {}
    for r_, c_ in zip(rows, cols):
        j, k = owner[c_]
        used.setdefault(j, []).append((k, r_))
    segs = []
    for j, lst in used.items():
        lst.sort()
        cur = [lst[0]]
        for item in lst[1:]:
            if item[0] - cur[-1][0] - 1 >= GAP_SPLIT:
                segs.append((j, cur))
                cur = []
            cur.append(item)
        segs.append((j, cur))
    rects, npins = [], 0
    for j, seg in segs:
        pins = runs[sel[j]].pins
        a, b = 3 * seg[0][0], 3 * seg[-1][0] + 3
        rects.append(_rect(pins[[a, b]]))
        npins += b - a + 1
    if any(not _apart(rects[a], rects[b]) for a, b in itertools.combinations(range(len(rects)), 2)):
        return math.inf, None
    if len(segs) > MAX_HEADERS:
        return math.inf, None
    total += HEADER_PENALTY * len(segs) + PIN_PENALTY * npins + BIG * max(0, MIN_HEADERS - len(segs))
    if not detail:
        return total, None
    hdrs = []
    for j, seg in segs:
        run = runs[sel[j]]
        a, b = 3 * seg[0][0], 3 * seg[-1][0] + 3
        names = ["GND"] * (b - a + 1)
        cost = 0.0
        for k, ui in seg:
            u = U[ui]
            cost += float(run.cost[ui, k])
            sig = list(reversed(u)) if run.swap[ui, k] else list(u)
            names[3 * k + 1 - a] = sig[0]
            if len(sig) == 2:
                names[3 * k + 2 - a] = sig[1]
        hdrs.append(dict(rot=run.rot, pins=names, xy=[tuple(map(float, p)) for p in run.pins[a:b + 1]], cost=cost))
    return total, hdrs


def _compact(h):
    """Drop a GND that follows another GND (a supply's spare pin next to the next slot's GND); pins move up."""
    keep = [k for k, s in enumerate(h["pins"]) if not (s == "GND" and k > 0 and h["pins"][k - 1] == "GND")]
    n = len(keep)
    h["pins"] = [h["pins"][k] for k in keep]
    h["xy"] = h["xy"][:n]
    return h


def search(S, smap, cv_names=None, log=print):
    """The cheapest legal set of MIN_HEADERS to MAX_HEADERS headers. Returns (cost, [header dicts])."""
    U = units(S)
    raw = smap.runs()
    runs = [Run(rot, pins, U, S) for rot, pins in raw]
    runs = [r for r in runs if r.nslots >= 1]
    log(f"   {len(U)} units ({sum(len(u) for u in U)} signals), {len(runs)} candidate rows "
        f"({sum(r.rot == 0 for r in runs)} vertical, {sum(r.rot == 90 for r in runs)} horizontal)")
    R = range(len(runs))
    singles = sorted(R, key=lambda r: evaluate([r], runs, U)[0])
    best = (math.inf, None)
    for start in singles[:STARTS]:
        sel, cost = [start], evaluate([start], runs, U)[0]
        while True:                                          # local search: add, swap, drop
            moves = []
            if len(sel) < MAX_HEADERS:
                moves += [sel + [r] for r in R if r not in sel]
            for i in range(len(sel)):
                moves += [sel[:i] + [r] + sel[i + 1:] for r in R if r not in sel]
                if len(sel) > 1:
                    moves.append(sel[:i] + sel[i + 1:])
            c, m = min(((evaluate(m, runs, U)[0], m) for m in moves), key=lambda t: t[0])
            if c >= cost - 1e-6:
                break
            sel, cost = m, c
        log(f"   start {start}: {len(sel)} rows, cost {cost:.0f}")
        if cost < best[0]:
            best = (cost, sel)
    cost, hdrs = evaluate(best[1], runs, U, detail=True)
    hdrs = [_compact(h) for h in hdrs]
    out = []
    for h in hdrs:
        x, y = h["xy"][0]
        out.append(dict(x=round(x, 3), y=round(y, 3), rot=h["rot"], rot_back=ROT_BACK[h["rot"]], pins=h["pins"],
                        xy=h["xy"], cost=round(h["cost"], 1)))
    out.sort(key=lambda h: (round(h["xy"][0][1] / 10), h["xy"][0][0]))
    for k, h in enumerate(out):
        h["name"] = str(k + 1)
    return cost, out
