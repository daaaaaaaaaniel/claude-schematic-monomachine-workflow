#!/usr/bin/env python3
"""Create machine-filter/machine-filter.kicad_pcb: the two board outlines side by side in one PCB file (KiKit's
multiboard workflow), ready for "Update PCB from schematic". Run once, before layout starts:

    python3 design/pcb_skeleton.py            # refuses to overwrite an existing PCB
    python3 design/pcb_skeleton.py --force    # overwrite (destroys any layout in the file)

Coordinates: boards.py / pinmap.py use the panel frame (front view, mm). In this PCB file
    CONTROL board  KiCad (x, y) = panel (x, y) + CONTROL_OFFSET
    MAIN board     KiCad (x, y) = panel (x, y) + MAIN_OFFSET
so the two boards sit side by side with a gap, and tools/separate.sh cuts each out by its BOX for fabrication.
Both boards share one layer stack (4 copper layers here): keep inner-layer copper inside the MAIN outline, and the
CONTROL board can still be fabricated as 2 layers (export F.Cu/B.Cu only; see HANDOFF.md).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boards  # noqa: E402

PCB = os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb")
CONTROL_OFFSET = (100.0, 50.0)          # as design/geom.py (OX, OY)
MAIN_OFFSET = (180.0, 50.0)             # 80 mm to the right: a 9.6 mm gap between the outlines
OUTLINE = {"control": (boards.BOARD_X, boards.BOARD_Y),          # panel frame
           "main": (boards.BOARD_X, (14.0, 114.0))}
OFFSET = {"control": CONTROL_OFFSET, "main": MAIN_OFFSET}
MARGIN = 4.0                            # the separation box reaches this far beyond each outline


def kicad_rect(board):
    (x0, x1), (y0, y1) = OUTLINE[board]
    dx, dy = OFFSET[board]
    return x0 + dx, y0 + dy, x1 + dx, y1 + dy


def box(board):
    """KiKit separation rectangle (KiCad mm) for `board`: its outline plus MARGIN."""
    x0, y0, x1, y1 = kicad_rect(board)
    return x0 - MARGIN, y0 - MARGIN, x1 + MARGIN, y1 + MARGIN


def mm(v):
    return pcbnew.FromMM(v)


def main():
    if os.path.exists(PCB) and "--force" not in sys.argv:
        raise SystemExit(f"{PCB} exists: layout may have started. Use --force to overwrite.")
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(4)
    for name in ("control", "main"):
        x0, y0, x1, y1 = kicad_rect(name)
        r = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_RECTANGLE)
        r.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        r.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        r.SetLayer(pcbnew.Edge_Cuts)
        r.SetWidth(mm(0.1))
        b.Add(r)
        t = pcbnew.PCB_TEXT(b)
        t.SetText(f"{name.upper()} board (front view; panel x, y + {OFFSET[name]})")
        t.SetPosition(pcbnew.VECTOR2I(mm(x0), mm(y0 - 2.5)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        b.Add(t)
    os.makedirs(os.path.dirname(PCB), exist_ok=True)
    b.Save(PCB)
    print(PCB)


if __name__ == "__main__":
    if "--boxes" in sys.argv:          # for tools/separate.sh: "board tlx tly brx bry" per line
        for name in ("main", "control"):
            print(name, *(f"{v:.2f}" for v in box(name)))
    else:
        main()
