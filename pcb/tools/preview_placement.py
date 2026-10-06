#!/usr/bin/env python3
"""Picture of a computed placement (auto_place.py JSON) on a scratch copy of the saved board; the board is untouched.

    python3 pcb/tools/preview_placement.py out/auto-place-main.json out.png [--crop main|control]
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))


def apply_offline(b, data):
    for ref, p in data["placements"].items():
        f = b.FindFootprintByReference(ref)
        back = data.get("side", "back") == "back"
        if (f.GetLayer() == pcbnew.B_Cu) != back:
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(p["rot"])
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(p["x"]), pcbnew.FromMM(p["y"])))


def main():
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    b = pcbnew.LoadBoard(BOARD)
    apply_offline(b, data)
    d = tempfile.mkdtemp()
    pcb = os.path.join(d, "p.kicad_pcb")
    pcbnew.SaveBoard(pcb, b)
    svg = os.path.join(d, "p.svg")
    subprocess.run(["kicad-cli", "pcb", "export", "svg", pcb, "--layers",
                    "B.Cu,F.Cu,B.Courtyard,F.Courtyard,B.Fab,Edge.Cuts", "--mode-single", "--fit-page-to-board",
                    "-o", svg], capture_output=True, check=True)
    png = os.path.join(d, "p.png")
    subprocess.run(["rsvg-convert", "-w", "2000", "-b", "white", svg, "-o", png], check=True)
    crop = sys.argv[sys.argv.index("--crop") + 1] if "--crop" in sys.argv else data["board"]
    # page spans KiCad x 100.35..250.45 (both outlines); crop to one board
    W = 2000 / (250.45 - 100.35)
    x0, x1 = (180.35, 250.45) if crop == "main" else (100.35, 170.45)
    subprocess.run(["convert", png, "-crop", f"{int((x1 - x0) * W) + 4}x10000+{int((x0 - 100.35) * W)}+0", "+repage", out],
                   check=True)
    print(out)


if __name__ == "__main__":
    main()
