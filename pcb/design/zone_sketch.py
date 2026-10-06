#!/usr/bin/env python3
"""Zone sketch for the main board (placement step 1, for d's review): the Seed3 at its USB-rule position, and one
rectangle per function group with its area budget. Quiet zones (CV, audio) vs noisy ones (power entry, digital).

Panel frame, seen from the front panel (as the floorplan pictures): the main board's back side, where the SMD parts
and the Seed3 go, is seen mirrored. Run from pcb/: python3 design/zone_sketch.py -> out/zone-sketch.png
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import floorplan as F  # noqa: E402

SEED = (33.615, 89.49, 180)     # USB end down, USB socket 26 mm inside the control board's edge (A2-C2 agree)
BOARD = (0.4, 14.0, 70.4, 114.0)
# name: (x0, y0, x1, y1, kind, groups budgeted in it)
ZONES = {
    "CV U2 (BASE, HP, LP, EQ F)": (51.5, 30.0, 70.0, 52.0, "quiet", ["cv_u2"]),
    "CV U1 (WIDTH, EQ G, DIST, SR)": (51.5, 52.0, 70.0, 74.0, "quiet", ["cv_u1"]),
    "-10 V ref U5": (36.0, 52.0, 46.5, 60.0, "quiet", ["ref_u5"]),
    "Audio in U3 / out U4": (3.0, 32.0, 31.0, 58.0, "quiet", ["audio_in", "audio_out"]),
    "microSD J15 (optional)": (3.0, 64.0, 31.0, 87.0, "noisy", ["microsd"]),
    "Power entry J13": (3.0, 92.0, 34.0, 113.0, "noisy", ["power"]),
    "J14 (USB, MIDI)": (51.5, 76.0, 70.0, 84.0, "noisy", ["expansion"]),
    "Seed3 supply filter": (51.5, 85.0, 70.0, 113.0, "noisy", ["seed3_filter"]),
    "free: headers, standoffs?": (1.0, 15.0, 70.0, 29.0, "free", []),
}
COLOR = {"quiet": "#2b7bd6", "noisy": "#e67e22", "free": "#9aa0a6"}


def main():
    budget = {b["group"]: b for b in json.load(open(os.path.join(HERE, "..", "out", "stage-groups.json")))["budget"]
              if b["board"] == "main"}
    budget["seed3_filter"] = {"with_routing_mm2": budget["seed3"]["with_routing_mm2"] - 939, "parts": 5}
    sp = F.seed_pads(SEED)
    fig, ax = plt.subplots(figsize=(7.4, 10.4))
    x0, y0, x1, y1 = BOARD
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.6, ec="#333"))
    rows = []
    for name, (a, b, c, d, kind, groups) in ZONES.items():
        area = (c - a) * (d - b)
        need = sum(budget[g]["with_routing_mm2"] for g in groups)
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc=COLOR[kind], alpha=0.16, ec=COLOR[kind], lw=1.2))
        txt = name + (f"\n{need:.0f} of {area:.0f} mm²" if groups else "")
        ax.text((a + c) / 2, (b + d) / 2, txt, ha="center", va="center", fontsize=7.2, color="#111")
        rows.append((name, kind, round(area), need))
    # the Seed3: body, socket pins, USB plug path
    xs = [p[0] for p in sp.values()]
    ys = [p[1] for p in sp.values()]
    ax.add_patch(Rectangle((min(xs) - 1.8, min(ys) - 3.1), max(xs) - min(xs) + 3.6, max(ys) - min(ys) + 6.2,
                           fill=False, ec="#444", lw=1.0, ls="--"))
    ux, uy, _ = F.usb_end(SEED)
    ax.add_patch(Rectangle((ux - F.PLUG_W / 2, uy), F.PLUG_W, y1 - uy, fc="#999", alpha=0.25, ec="none"))
    ax.text(ux, (uy + y1) / 2, "USB plug path\n(flat parts only)", ha="center", va="center", fontsize=6.5)
    pin_groups = {"codec 16-19": range(16, 20), "MIDI 14-15": (14, 15), "LED 12": (12,), "mux sel 8-10": (8, 9, 10),
                  "SD 2-7": range(2, 8), "3V3_A 21": (21,), "ADC 22-32": range(22, 33), "USB 36-37": (36, 37),
                  "VIN 39": (39,)}
    for label, pins in pin_groups.items():
        pts = [sp[str(p)] for p in pins]
        px = pts[0][0]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o", ms=3.2, color="#c0392b" if "ADC" in label or
                "codec" in label else "#555")
        ys_ = [p[1] for p in pts]
        ax.text(px + (1.6 if px > 40 else -1.6), sum(ys_) / len(ys_), label, fontsize=6, va="center",
                ha="left" if px > 40 else "right", color="#222")
    ax.text((min(xs) + max(xs)) / 2, min(ys) - 1.5, "SEED3 (back)\nunder: flat parts only", ha="center",
            va="bottom", fontsize=7)
    ax.set_xlim(x0 - 2, x1 + 2)
    ax.set_ylim(y1 + 2, y0 - 6)
    ax.set_aspect("equal")
    ax.set_title("MAIN board, 70 × 100 mm, seen from the panel (back side mirrored)\n"
                 "blue = quiet, orange = noisy, grey = free", fontsize=9)
    ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "..", "out", "zone-sketch.png"), dpi=160)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
