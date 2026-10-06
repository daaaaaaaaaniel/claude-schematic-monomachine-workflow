"""Footprint geometry for the floorplans, through KiCad's pcbnew module.

Coordinates are the panel frame seen from the front (boards.py: x right, y down, mm). Both boards sit behind the
panel and are drawn in the same frame: a part on a board's back side is mirrored, as KiCad flips it.
  control board: 'front' faces the panel (jacks, pots, LEDs); 'back' faces the main board.
  main board:    'front' faces the control board; 'back' is the outer side (SMD parts, the Seed3, power header).
"""
import math
import os

import numpy as np
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_LIB = os.path.join(HERE, "..", "lib", "filter-module.pretty")
STOCK = os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
OX, OY = 100.0, 50.0
BOARD = pcbnew.BOARD()


def load(fpid):
    lib, name = fpid.split(":")
    path = PROJECT_LIB if lib == "filter-module" else os.path.join(STOCK, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found")
    BOARD.Add(fp)
    return fp


def put(fp, x, y, rot, back):
    if fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y)))
    fp.SetOrientationDegrees(rot)
    if back:                                   # mirror in x only: a vertical part keeps its pin order down y
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)


def pads(fp):
    """{number: [(x, y, w, h, through_hole)]}"""
    out = {}
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        out.setdefault(p.GetNumber(), []).append(
            (pcbnew.ToMM(p.GetPosition().x) - OX, pcbnew.ToMM(p.GetPosition().y) - OY,
             pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))
    return out


def courtyard(fp):
    """Bounding box of the courtyard (either side), or of the pads if the footprint has none."""
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            bb = g.GetBoundingBox()
            xs += [pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetRight()) - OX]
            ys += [pcbnew.ToMM(bb.GetTop()) - OY, pcbnew.ToMM(bb.GetBottom()) - OY]
    if not xs:
        for plist in pads(fp).values():
            for x, y, w, h, _ in plist:
                xs += [x - w / 2, x + w / 2]
                ys += [y - h / 2, y + h / 2]
    return min(xs), min(ys), max(xs), max(ys)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Board:
    """Two occupancy grids (front, back) over a board outline; through-hole pads block both sides."""
    RES = 0.1

    def __init__(self, x0, y0, x1, y1, edge=0.4):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.nx, self.ny = int(round((x1 - x0) / self.RES)), int(round((y1 - y0) / self.RES))
        self.grid = {s: np.zeros((self.ny, self.nx), bool) for s in ("front", "back")}
        self.tall_ok = np.ones((self.ny, self.nx), bool)       # False where only flat parts may go (under the Seed)
        e = int(edge / self.RES)
        for g in self.grid.values():
            g[:e, :] = g[-e:, :] = g[:, :e] = g[:, -e:] = True
        self.items = []

    def _sl(self, x0, y0, x1, y1):
        i0, i1 = int(np.floor((y0 - self.y0) / self.RES)), int(np.ceil((y1 - self.y0) / self.RES))
        j0, j1 = int(np.floor((x0 - self.x0) / self.RES)), int(np.ceil((x1 - self.x0) / self.RES))
        return slice(max(i0, 0), max(i1, 0)), slice(max(j0, 0), max(j1, 0))

    def mark(self, side, box, grow=0.0):
        x0, y0, x1, y1 = box
        self.grid[side][self._sl(x0 - grow, y0 - grow, x1 + grow, y1 + grow)] = True

    def integral(self, side):
        """Summed-area table of the occupancy grid of `side` (for O(1) "is this box free?" queries)."""
        I = np.zeros((self.ny + 1, self.nx + 1), np.int32)
        I[1:, 1:] = self.grid[side].cumsum(0).cumsum(1)
        return I

    def box_free(self, I, x0, y0, x1, y1):
        """Vectorised: True where the boxes (numpy arrays of mm) are inside the board and free in integral I."""
        j0 = np.floor((np.asarray(x0) - self.x0) / self.RES).astype(int)
        j1 = np.ceil((np.asarray(x1) - self.x0) / self.RES).astype(int)
        i0 = np.floor((np.asarray(y0) - self.y0) / self.RES).astype(int)
        i1 = np.ceil((np.asarray(y1) - self.y0) / self.RES).astype(int)
        inside = (j0 >= 0) & (i0 >= 0) & (j1 <= self.nx) & (i1 <= self.ny)
        j0, j1 = np.clip(j0, 0, self.nx), np.clip(j1, 0, self.nx)
        i0, i1 = np.clip(i0, 0, self.ny), np.clip(i1, 0, self.ny)
        S = I[i1, j1] - I[i0, j1] - I[i1, j0] + I[i0, j0]
        return inside & (S == 0)

    def mark_flat_only(self, box):
        self.tall_ok[self._sl(*box)] = False

    def add(self, ref, fp, side, keep_pad=0.45, keep_body=0.3, body=True, label=None):
        """Record a placed footprint: its courtyard on `side`, its through-hole pads (plus keep_pad) on both."""
        box = courtyard(fp)
        if body:
            self.mark(side, box, keep_body)
        pp = pads(fp)
        for plist in pp.values():
            for x, y, w, h, th in plist:
                for s in (("front", "back") if th else (side,)):
                    self.mark(s, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), keep_pad)
        self.items.append(dict(ref=ref, side=side, box=box, pads=pp, label=label or ref))
        return pp

    def free_spot(self, w, h, tx, ty, sides, tall=False):
        """Centre of the free w x h box nearest (tx, ty), free on every side in `sides`."""
        occ = np.zeros_like(self.grid["front"])
        for s in sides:
            occ |= self.grid[s]
        if tall:
            occ |= ~self.tall_ok
        I = np.zeros((self.ny + 1, self.nx + 1), np.int32)
        I[1:, 1:] = occ.cumsum(0).cumsum(1)
        hw, hh = int(np.ceil(w / self.RES)), int(np.ceil(h / self.RES))
        if hw >= self.nx or hh >= self.ny:
            return None
        S = I[hh:, hw:] - I[:-hh, hw:] - I[hh:, :-hw] + I[:-hh, :-hw]
        ii, jj = np.nonzero(S == 0)
        if not len(ii):
            return None
        cx, cy = self.x0 + (jj + hw / 2) * self.RES, self.y0 + (ii + hh / 2) * self.RES
        k = np.argmin((cx - tx) ** 2 + (cy - ty) ** 2)
        return float(cx[k]), float(cy[k])

    def place(self, ref, fpid, target, side, rots=(0, 90), through_hole=False, tall=False, gap=0.3, label=None):
        """Put fpid at the free spot nearest target (trying each rotation), record it, return its pads."""
        best = None
        for rot in rots:
            fp = load(fpid)
            put(fp, 0, 0, rot, side == "back")
            x0, y0, x1, y1 = courtyard(fp)
            sides = ("front", "back") if through_hole else (side,)
            r = self.free_spot(x1 - x0 + 2 * gap, y1 - y0 + 2 * gap, *target, sides, tall)
            if r is None:
                continue
            cx, cy = r[0] - (x0 + x1) / 2, r[1] - (y0 + y1) / 2
            d = dist(r, target)
            if best is None or d < best[0]:
                best = (d, rot, cx, cy, fp)
        if best is None:
            raise SystemExit(f"no room for {ref}")
        _, rot, x, y, fp = best
        put(fp, x, y, rot, side == "back")
        pp = self.add(ref, fp, side, body=True, label=label)
        self.items[-1].update(x=round(x, 2), y=round(y, 2), rot=rot, fp=fpid)
        return pp
