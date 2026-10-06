"""Board-to-board header search (d, 2026-10-06): three or four single-row 2.54 mm headers, any orientation, any
length, instead of the two fixed rows of the first floorplan.

Rather than trying every way to split the 35-odd pins, the signals choose:
  1. Each crossing signal has a control-board end and a main-board end. The candidate groupings are the four natural
     groups (audio, CV, pots and digital, power), the three-header merges of them, and k-means clusterings (k = 3, 4)
     of the signals' midpoints.
  2. Each group's header gets a fixed pin pattern (GND first; analog signals in pairs with a GND after each pair; then
     the digital ones likewise, so a switching line never sits next to an analog one; each supply flanked by GNDs),
     so its length follows from its group.
  3. Legal sites only: every pin clear of the control board's front parts (their pins and bodies), the socket's body
     clear on the control board's back, inside both outlines, and every pin at least SEED_MIN from every Seed3 pin
     (centre to centre: room for an iron between the header and the Seed's socket).
  4. Each legal site is scored cheaply (signals to pins by minimum-cost matching, distance-weighted as the floorplan);
     the best few sites per group are combined, rejecting overlaps, and the cheapest combination wins.
The floorplan then alternates: headers for a given Seed3 position, the Seed3 position for those headers, until both
settle.
"""
import itertools
import math

import numpy as np
from scipy.optimize import linear_sum_assignment

from geom import dist

PITCH = 2.54
SEED_MIN = 5.08            # header pin to Seed3 pin, centre to centre (d: hand soldering)
PAD_KEEP = 1.85            # half-size of the keep-clear square round a header pin on the control board's front
BODY_HALF = 1.27 + 0.4     # half-width of a header body plus clearance
BODY_GAP = 1.0             # between two headers' bodies
EDGE = 2.5                 # header pin to board edge
HEADER_PENALTY = 15.0      # weighted mm per header: near-ties go to fewer headers
TOP_K = 12                 # sites kept per group for the combination step
RADIUS = 35.0              # sites considered within this distance of a group's centre
STEP = 0.635
DIRS = {0: (0.0, 1.0), 90: (1.0, 0.0), 180: (0.0, -1.0), 270: (-1.0, 0.0)}   # pin k = pin 1 + k * PITCH * dir
ROT_BACK = {0: 0, 90: 270, 180: 180, 270: 90}   # the socket on the control board's back that lands pin k on pin k
POWER = ("+12V", "-12V", "+3V3_A")
DIGITAL = ("MUX_A", "MUX_B", "MUX_C", "LED_A")       # switching lines: never paired with an analog one
GROUP_OF = {"IN_L": "audio", "IN_R": "audio", "OUT_L": "audio", "OUT_R": "audio",
            "POT_VOL": "pots", "POT_MUX": "pots", "MUX_A": "pots", "MUX_B": "pots", "MUX_C": "pots", "LED_A": "pots",
            "+12V": "power", "-12V": "power", "+3V3_A": "power"}


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


def pattern(group):
    """Pin list for a group's header (signal slots are filled in later): GND, the analog signals in pairs each
    followed by a GND, then the digital ones the same way (so a switching line never sits next to an analog one),
    then each supply followed by a GND."""
    pins = ["GND"]
    for k in ("A", "D"):
        sig = [s for s in group if kind(s) == k]
        for j in range(0, len(sig), 2):
            pins += [k] * len(sig[j:j + 2]) + ["GND"]
    pins += ["P", "GND"] * sum(1 for s in group if kind(s) == "P")
    return pins


def groupings(S, cv_names):
    """Candidate groupings: the natural four, their three-group merges, and k-means (k = 3, 4) of the midpoints."""
    nat = {"audio": [], "cv": [], "pots": [], "power": []}
    for s in S:
        nat[GROUP_OF.get(s, "cv")].append(s)
    four = [nat["audio"], nat["cv"], nat["pots"], nat["power"]]
    out = [four]
    for a, b in itertools.combinations(range(4), 2):
        out.append([g for k, g in enumerate(four) if k not in (a, b)] + [four[a] + four[b]])
    names = list(S)
    mid = np.array([((S[s][0][0] + S[s][1][0]) / 2, (S[s][0][1] + S[s][1][1]) / 2) for s in names])
    rng = np.random.default_rng(1)
    for k in (3, 4):
        best = None
        for _ in range(30):
            c = mid[rng.choice(len(mid), k, replace=False)]
            for _ in range(50):
                lab = np.argmin(((mid[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
                c = np.array([mid[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
            sse = float(((mid - c[lab]) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, lab)
        out.append([[names[i] for i in range(len(names)) if best[1][i] == j] for j in range(k)])
    seen, uniq = set(), []
    for g in out:
        key = frozenset(frozenset(x) for x in g if x)
        if key not in seen:
            seen.add(key)
            uniq.append([sorted(x) for x in g if x])
    return uniq


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


def score_site(group, pins, xy, S):
    """Cheapest assignment of the group's signals to the site's signal/supply pins; returns (cost, pin names)."""
    names = list(pins)
    total = 0.0
    for k in ("A", "D", "P"):
        members = [s for s in group if kind(s) == k]
        slots = [i for i, p in enumerate(pins) if p == k]
        if not members:
            continue
        C = np.array([[S[s][2] * (dist(S[s][0], xy[i]) + dist(xy[i], S[s][1])) for i in slots] for s in members])
        r, c = linear_sum_assignment(C)
        total += float(C[r, c].sum())
        for a, b in zip(r, c):
            names[slots[b]] = members[a]
    return total, names


def best_sites(group, S, smap):
    pins = pattern(group)
    mids = np.array([((S[s][0][0] + S[s][1][0]) / 2, (S[s][0][1] + S[s][1][1]) / 2) for s in group])
    center = tuple(mids.mean(0))
    meta, xys = smap.sites(len(pins), center, RADIUS)
    scored = []
    for m, xy in zip(meta, xys):
        c, names = score_site(group, pins, xy, S)
        scored.append((c, m, xy, names))
    scored.sort(key=lambda t: t[0])
    kept = []
    for t in scored:                    # the best few, at least a pitch apart from each other
        if all(dist(t[2][0], u[2][0]) >= PITCH or t[1][2] != u[1][2] for u in kept):
            kept.append(t)
        if len(kept) >= TOP_K:
            break
    return kept


def _rect(xy):
    return (xy[:, 0].min() - BODY_HALF, xy[:, 1].min() - BODY_HALF, xy[:, 0].max() + BODY_HALF, xy[:, 1].max() + BODY_HALF)


def _apart(a, b):
    return a[2] + BODY_GAP <= b[0] or b[2] + BODY_GAP <= a[0] or a[3] + BODY_GAP <= b[1] or b[3] + BODY_GAP <= a[1]


def search(S, smap, cv_names, log=print):
    """The cheapest legal set of headers over all candidate groupings. Returns (cost, [header dicts])."""
    cache = {}
    best = None
    for G in groupings(S, cv_names):
        lists = []
        for g in G:
            key = tuple(g)
            if key not in cache:
                cache[key] = best_sites(g, S, smap)
            lists.append(cache[key])
        if any(not l for l in lists):
            continue
        rects = [[_rect(t[2]) for t in l] for l in lists]
        cur = None
        for combo in itertools.product(*[range(len(l)) for l in lists]):
            cost = sum(lists[i][j][0] for i, j in enumerate(combo))
            if cur is not None and cost >= cur[0]:
                continue
            if all(_apart(rects[a][combo[a]], rects[b][combo[b]]) for a, b in itertools.combinations(range(len(G)), 2)):
                cur = (cost, combo)
        if cur is None:
            continue
        total = cur[0] + HEADER_PENALTY * len(G)
        log(f"   grouping {[len(g) for g in G]} signals -> {len(G)} headers: cost {total:.0f}")
        if best is None or total < best[0]:
            best = (total, [lists[i][j] for i, j in enumerate(cur[1])])
    if best is None:
        raise SystemExit("no legal set of headers")
    hdrs = []
    for c, (x, y, rot), xy, names in best[1]:
        hdrs.append(dict(x=x, y=y, rot=rot, rot_back=ROT_BACK[rot], pins=names, xy=[tuple(map(float, p)) for p in xy],
                         cost=round(c, 1)))
    hdrs.sort(key=lambda h: (round(h["xy"][0][1] / 10), h["xy"][0][0]))
    for k, h in enumerate(hdrs):
        h["name"] = str(k + 1)
    return best[0], hdrs
