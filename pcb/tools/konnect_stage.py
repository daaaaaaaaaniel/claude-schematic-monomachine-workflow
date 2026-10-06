#!/usr/bin/env python3
"""Apply out/stage-groups.json (design/stage_groups.py) to the board open in KiCad, through Konnect:
every part to its group cluster beside its board (one undo step), the optional standoff holes, a label per group on
User.Comments, then save. Reads the result back live and checks each placement landed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
from konnect_call import Client  # noqa: E402
import groups as G  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
LABEL = {"seed3": "1 SEED3 (+ supply filter)", "cv_u2": "2 CV U2: BASE (1V/OCT), HP RES, LP RES, EQ FREQ",
         "cv_u1": "2 CV U1: WIDTH (1V/OCT), EQ GAIN, DIST, SMPL RATE", "audio_in": "3 AUDIO IN U3",
         "audio_out": "3 AUDIO OUT U4", "ref_u5": "4 -10V REF U5", "power": "5 POWER ENTRY J13",
         "microsd": "6 microSD J15 (optional)", "expansion": "6 EXPANSION J14", "headers": "7 HEADERS",
         "mux_u6": "POT MUX U6", "leds_u7": "LED DRIVERS U7", "leds_u8": "LED DRIVERS U8",
         "panel": "PANEL PARTS (fixed by the panel)"}


def main():
    st = json.load(open(os.path.join(HERE, "..", "out", "stage-groups.json")))
    c = Client()
    try:
        r = c.call("set_component_placements", {"board": BOARD, "placements": st["placements"]})
        print("placements:", {k: v for k, v in r.items() if not isinstance(v, list)} if isinstance(r, dict) else r)
        if os.environ.get("PARTS_ONLY"):
            got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
            off = [p["reference"] for p in st["placements"] if abs(got[p["reference"]]["x"] - p["x"]) > 0.01
                   or abs(got[p["reference"]]["y"] - p["y"]) > 0.01]
            print(f"readback: {len(st['placements']) - len(off)} at their staged position; off: {off}")
            print("save:", c.call("save_project", {}))
            return
        have = {x["reference"] for x in c.call("get_component_list", {"board": BOARD})["components"]}
        # standoffs (optional, d): board-only M3 holes, parked under each board's clusters
        boxes = st["boxes"]
        for board, refs in G.STANDOFFS.items():
            b = [x for x in boxes if x["x0"] > 250] if board == "main" else [x for x in boxes if x["x0"] < 100]
            x0 = min(x["x0"] for x in b)
            y0 = max(x["y0"] + x["h"] for x in b) + 12
            for i, ref in enumerate(refs):
                if ref not in have:
                    c.call("add_mounting_hole", {"board": BOARD, "reference": ref, "x": x0 + 4 + 8 * i, "y": y0,
                                                 "drill_diameter": 3.2})
            c.call("add_board_text", {"board": BOARD, "text": "8 STANDOFFS (optional)", "x": x0, "y": y0 - 6,
                                      "layer": "User.Comments", "size": 1.5})
        for b in boxes:
            c.call("add_board_text", {"board": BOARD, "text": LABEL.get(b["group"], b["group"]), "x": b["x0"],
                                      "y": b["y0"] + 1.2, "layer": "User.Comments", "size": 1.2})
        # live readback
        got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
        off = [p["reference"] for p in st["placements"]
               if abs(got[p["reference"]]["x"] - p["x"]) > 0.01 or abs(got[p["reference"]]["y"] - p["y"]) > 0.01]
        print(f"readback: {len(got)} footprints; {len(st['placements']) - len(off)} at their staged position; off: {off}")
        print("save:", c.call("save_project", {}))
    finally:
        c.close()


if __name__ == "__main__":
    main()
