#!/usr/bin/env python3
"""Picture of one whole board as saved (copper both sides, courtyards, part outlines), seen from the front.

    python3 pcb/tools/render_board.py main|control out.png
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
AREA = {"main": (180.0, 63.5, 251.0, 164.5), "control": (100.0, 60.3, 171.0, 168.2)}   # KiCad mm, with margin
PAGE_X0, PAGE_Y0, PAGE_W = 100.35, 60.7, 150.1          # the svg page spans both outlines (fit to board)


def main():
    board, out = sys.argv[1], sys.argv[2]
    d = tempfile.mkdtemp()
    svg, png = os.path.join(d, "b.svg"), os.path.join(d, "b.png")
    subprocess.run(["kicad-cli", "pcb", "export", "svg", BOARD, "--layers",
                    "B.Cu,F.Cu,B.Courtyard,F.Courtyard,B.Fab,F.Fab,Edge.Cuts", "--mode-single",
                    "--fit-page-to-board", "--exclude-drawing-sheet", "-o", svg], capture_output=True, check=True)
    W = 4000
    subprocess.run(["rsvg-convert", "-w", str(W), "-b", "white", svg, "-o", png], check=True)
    s = W / PAGE_W
    x0, y0, x1, y1 = AREA[board]
    subprocess.run(["convert", png, "-crop",
                    f"{int((x1 - x0) * s)}x{int((y1 - y0) * s)}+{max(0, int((x0 - PAGE_X0) * s))}+{max(0, int((y0 - PAGE_Y0) * s))}",
                    "+repage", "-resize", "1100x", out], check=True)
    print(out)


if __name__ == "__main__":
    main()
