#!/usr/bin/env python3
"""Re-match the CV channels to Seed3 ADC pins from the placed board (pin map follows the layout, d 2026-10-06).

Each channel keeps the op-amp section its parts were placed beside (SECTIONS below, as in design/placement.py).
ADC pins are matched to the placed section outputs by minimum weighted straight-line distance (1V/OCT x6, other CV
x3, as floorplan.py), with FIXED pins held (their traces are drawn). The two pot signals take the pins left over,
nearest the Seed3's top (they arrive from the board-to-board headers, placed last).

    python3 tools/rematch_adc.py          # print the proposal
    python3 tools/rematch_adc.py --write  # write it into design/pinmap.py (then build.sh, docs, PCB update)
"""
import math
import os
import re
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
from konnect_call import Client  # noqa: E402
import boards  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
PINMAP = os.path.join(HERE, "..", "design", "pinmap.py")
SECTIONS = {"BASE": ("U2", 1), "HPRES": ("U2", 2), "LPRES": ("U2", 3), "EQF": ("U2", 4),
            "WIDTH": ("U1", 1), "EQG": ("U1", 2), "DIST": ("U1", 3), "SRR": ("U1", 4)}
OUT_PIN = {1: "1", 2: "7", 3: "8", 4: "14"}
FIXED = {"BASE": "23"}                      # trace drawn in step 3
ADC = [str(k) for k in range(22, 33)]       # A0-A10; A11 (pin 35) stays free, next to USB D-


def main():
    c = Client()
    try:
        pads = {r: {p["number"]: (p["x"], p["y"]) for p in c.call("get_component_pads", {"board": BOARD,
                                                                                           "reference": r})["pads"]}
                for r in ("A1", "U1", "U2")}
    finally:
        c.close()
    chans = [n for n in boards.CV_NAMES if n not in FIXED]
    free = [p for p in ADC if p not in FIXED.values()]
    w = {n: 6.0 if n in boards.ONE_V_OCT else 3.0 for n in chans}
    cost = np.array([[w[n] * math.dist(pads[SECTIONS[n][0]][OUT_PIN[SECTIONS[n][1]]], pads["A1"][p]) for p in free]
                     for n in chans])
    ri, ci = linear_sum_assignment(cost)
    adc = dict(FIXED)
    adc.update({chans[i]: free[j] for i, j in zip(ri, ci)})
    left = sorted((p for p in ADC if p not in adc.values()), key=int)
    pots = {"POT_VOL": left[0], "POT_MUX": left[1]}
    print("channel  section  ADC pin  straight-line mm")
    for n in boards.CV_NAMES:
        u, s = SECTIONS[n]
        d = math.dist(pads[u][OUT_PIN[s]], pads["A1"][adc[n]])
        print(f"{n:6s}   {u}{'ABCD'[s - 1]}      {adc[n]:>3}      {d:5.1f}{'  (1V/OCT)' if n in boards.ONE_V_OCT else ''}")
    print("pots:", pots, " unused:", [p for p in left[2:]])
    if "--write" in sys.argv:
        seed_adc = {f"ADC_{n}": adc[n] for n in boards.CV_NAMES}
        seed_adc.update(pots)
        seed_adc = dict(sorted(seed_adc.items(), key=lambda kv: int(kv[1])))
        t = open(PINMAP).read()
        t = re.sub(r"^SEED_ADC = .*$", "SEED_ADC = " + repr(seed_adc).replace("'", '"'), t, count=1, flags=re.M)
        t = re.sub(r"^ADC_UNIT = .*$", "ADC_UNIT = " + repr({n: SECTIONS[n] for n in boards.CV_NAMES})
                   .replace("'", '"'), t, count=1, flags=re.M)
        t = re.sub(r"^# 2026-10-06 \(d\): WIDTH and EQF swapped.*$",
                   "# 2026-10-06: ADC_UNIT and SEED_ADC re-matched to the placed U1/U2 (tools/rematch_adc.py); "
                   "each quad carries one 1V/OCT channel, on section A", t, count=1, flags=re.M)
        open(PINMAP, "w").write(t)
        print("written to design/pinmap.py")


if __name__ == "__main__":
    main()
