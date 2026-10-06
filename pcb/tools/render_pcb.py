#!/usr/bin/env python3
"""Picture of machine-filter.kicad_pcb for review: both boards seen from the panel side (KiCad's top view).

Each footprint is drawn as its courtyard (or bounding box) with its reference; blue = front side, orange = back
side; pads as small dots; ratsnest lines (straight, unrouted) for parts already on a board. Parked parts below the
outlines are drawn too.

    python3 tools/render_pcb.py [out.png]          (from pcb/; default out/pcb-placement.png)
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
import pcbnew  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "out", "pcb-placement.png")
MM = pcbnew.ToMM
COL = {"front": "#2b7bd6", "back": "#e67e22"}


def crt(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            bb = g.GetBoundingBox()
            xs += [MM(bb.GetLeft()), MM(bb.GetRight())]
            ys += [MM(bb.GetTop()), MM(bb.GetBottom())]
    if not xs:
        bb = fp.GetBoundingBox(False)
        return MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())
    return min(xs), min(ys), max(xs), max(ys)


def main():
    b = pcbnew.LoadBoard(PCB)
    outlines = []
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            bb = d.GetBoundingBox()
            outlines.append((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())))
    fig, ax = plt.subplots(figsize=(16, 15))
    for x0, y0, x1, y1 in outlines:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.5, ec="black"))
    on_board = lambda x, y: any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in outlines)
    pad_xy = {}
    for fp in b.GetFootprints():
        side = "back" if fp.IsFlipped() else "front"
        x0, y0, x1, y1 = crt(fp)
        placed = on_board((x0 + x1) / 2, (y0 + y1) / 2)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=COL[side], alpha=0.18 if placed else 0.10,
                               ec=COL[side], lw=0.8, hatch="//" if side == "back" else None))
        fs = 6 if (x1 - x0) * (y1 - y0) < 40 else 8
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, fp.GetReference(), ha="center", va="center", fontsize=fs)
        for p in fp.Pads():
            x, y = MM(p.GetPosition().x), MM(p.GetPosition().y)
            ax.plot(x, y, ".", ms=2, color="#333")
            if placed and p.GetNetname():
                pad_xy.setdefault(p.GetNetname(), []).append((x, y))
    # ratsnest among placed parts: a minimum spanning tree per net (Prim), ground nets faint
    for net, pts in pad_xy.items():
        if len(pts) < 2:
            continue
        gnd = net.endswith("GND")
        done, rest = [pts[0]], pts[1:]
        while rest:
            d, a, c = min(((ax_ - bx) ** 2 + (ay - by) ** 2, (ax_, ay), (bx, by))
                          for ax_, ay in done for bx, by in rest)
            ax.plot([a[0], c[0]], [a[1], c[1]], lw=0.3 if gnd else 0.5, color="#bbb" if gnd else "#8e44ad",
                    alpha=0.6)
            done.append(c)
            rest.remove(c)
    for t in b.GetDrawings():
        if t.GetLayer() == pcbnew.Cmts_User and t.GetClass() == "PCB_TEXT":
            ax.text(MM(t.GetPosition().x), MM(t.GetPosition().y), t.GetText(), fontsize=7, color="#555",
                    va="bottom")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.autoscale_view()
    ax.set_title("machine-filter.kicad_pcb, top view (from the panel side). Blue = front side, orange hatched = "
                 "back side; purple = unrouted connections between placed parts", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT, dpi=110)
    print(OUT)


if __name__ == "__main__":
    main()
