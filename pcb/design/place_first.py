#!/usr/bin/env python3
"""First placement step: bring every footprint from the schematic into machine-filter.kicad_pcb (once).

What it does, and nothing more:
  * every part in out/drawn.net (the schematic's netlist) becomes a footprint, with its nets and its link to the
    schematic symbol (so KiCad's "Update PCB from schematic" recognises it later);
  * parts whose position is fixed or already decided go there:
      - panel parts (jacks, pots, LEDs): their panel positions from boards.py, on the CONTROL board's front;
      - board-to-board headers JA/JB and the Seed3 A1: where pinmap.py has them (parked decision, d 2026-10-06);
      - ICs, power entry, bulky capacitors, J14/J15: pinmap.MAIN_PLACEMENT / CONTROL_PLACEMENT (the floorplan);
  * every other part (resistors, small capacitors, ferrites) is parked in a labelled grid just below its own
    board's outline, grouped by schematic page, for the next step (placing them by docs/placement-guide.md).

Coordinates: KiCad (x, y) = panel (x, y) + OFFSET[board] (design/pcb_skeleton.py). Back-side parts are flipped
left-right after rotation, exactly as design/geom.put does, so pinmap positions land where the floorplan had them.

Run from pcb/ after tools/build.sh:  python3 design/place_first.py
It refuses to run on a PCB that already holds footprints (that would be layout work); --force starts over
from the outline-only skeleton.
"""
import os
import sys
from collections import defaultdict

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boards  # noqa: E402
import pinmap  # noqa: E402
from pcb_skeleton import OFFSET, PCB, kicad_rect  # noqa: E402
from sexpr import parse  # noqa: E402

NETLIST = os.path.join(HERE, "..", "out", "drawn.net")
PROJECT_LIB = os.path.join(HERE, "..", "lib", "filter-module.pretty")
STOCK = os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
PARK_GAP = 8.0          # mm between a board's bottom edge and its parking grid


def mm(v):
    return pcbnew.FromMM(v)


def front_rotation(p):  # the panel parts' orientations (same rule as floorplan.front_rotation)
    x, y = p.xy
    if p.kind == "POT" and y > 100:
        return 180
    if p.kind == "JACK" and y < boards.IN_Y:
        return 180
    if p.kind in ("JACK_CV", "LEDRG"):
        return 90
    return 0


# ------------------------------------------------------------------------------------------------ netlist
def kv(e, key):
    for x in e[1:]:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def read_netlist():
    root = parse(open(NETLIST).read())[0]
    comps, nets = {}, {}
    for c in kv(root, "components")[1:]:
        ref = kv(c, "ref")[1]
        props = {kv(p, "name")[1]: (kv(p, "value") or [None, ""])[1] for p in c[1:]
                 if isinstance(p, list) and p[0] == "property"}
        sheet = kv(kv(c, "sheetpath"), "tstamps")[1]
        stamps = kv(c, "tstamps")[1].split()
        if kv(c, "description"):
            props.setdefault("Description", kv(c, "description")[1])
        comps[ref] = dict(ref=ref, value=kv(c, "value")[1], fp=kv(c, "footprint")[1], props=props,
                          path=sheet + stamps[0], dnp="dnp" in props)
    for n in kv(root, "nets")[1:]:
        name = kv(n, "name")[1]
        nets[name] = [(kv(x, "ref")[1], kv(x, "pin")[1]) for x in n[1:] if isinstance(x, list) and x[0] == "node"]
    return comps, nets


# ------------------------------------------------------------------------------------------------ placement
def decided_positions():
    """{ref: (board, side, panel x, y, rotation)} for every part whose place is already decided."""
    pos = {}
    for p in boards.board():
        if p.xy:
            pos[p.ref] = ("control", "front", p.xy[0], p.xy[1], front_rotation(p))
    for n, (x, y, rot_main, rot_ctl) in pinmap.HEADER_POS.items():
        pos[f"JB{n}"] = ("main", "front", x, y, rot_main)
        pos[f"JA{n}"] = ("control", "back", x, y, rot_ctl)
    pos["A1"] = ("main", "back", *pinmap.SEED)
    for ref, (x, y, rot) in pinmap.MAIN_PLACEMENT.items():
        pos[ref] = ("main", "back", x, y, rot)
    for ref, (x, y, rot) in pinmap.CONTROL_PLACEMENT.items():
        pos[ref] = ("control", "back", x, y, rot)
    return pos


def put(fp, board, x, y, rot, back):
    """As design/geom.put, with this board's offset."""
    if fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(0)
    dx, dy = OFFSET[board]
    fp.SetPosition(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
    fp.SetOrientationDegrees(rot)
    if back:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)


def load(fpid):
    lib, name = fpid.split(":")
    path = PROJECT_LIB if lib == "filter-module" else os.path.join(STOCK, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def size(fp):
    bb = fp.GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def main():
    b = pcbnew.LoadBoard(PCB)
    if len(b.GetFootprints()) and "--force" not in sys.argv:
        raise SystemExit(f"{PCB} already holds {len(b.GetFootprints())} footprints: layout has started. "
                         "--force starts again from the outline-only skeleton.")
    if len(b.GetFootprints()):
        for fp in list(b.GetFootprints()):
            b.Remove(fp)
        for d in list(b.Drawings()):
            if d.GetLayer() == pcbnew.Cmts_User and d.GetClass() == "PCB_TEXT" and "parked" in d.GetText():
                b.Remove(d)

    comps, nets = read_netlist()
    pos = decided_positions()
    missing = set(pos) - set(comps)
    assert not missing, f"placement for parts not in the schematic: {missing}"

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        netinfo[name] = ni
    pad_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes}

    parked = defaultdict(list)
    for ref, c in sorted(comps.items(), key=lambda kv_: (kv_[1]["props"].get("Sheetfile", ""), kv_[0])):
        fp = load(c["fp"])
        b.Add(fp)                                   # add before querying (pcbnew segfaults otherwise)
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname(c["props"].get("Sheetname", ""))
        fp.SetSheetfile(c["props"].get("Sheetfile", ""))
        if c["props"].get("Description"):
            fp.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(c["props"]["Description"])
        for key in ("LCSC", "MPN", "Assembly", "Board"):
            if c["props"].get(key):
                fp.SetField(key, c["props"][key])
                fp.GetField(key).SetVisible(False)
        if c["dnp"]:
            fp.SetDNP(True)
        for pad in fp.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        board = c["props"].get("Board")
        assert board in ("main", "control"), (ref, board)
        if ref in pos:
            pboard, side, x, y, rot = pos[ref]
            assert pboard == board, (ref, pboard, board)
            put(fp, board, x, y, rot, side == "back")
        else:
            parked[board].append((c["props"].get("Sheetname", ""), fp))

    # park the rest below each board, one row per schematic page, on the side they will be soldered to
    for board, items in parked.items():
        x0, _, x1, y1 = kicad_rect(board)
        y = y1 + PARK_GAP
        by_sheet = defaultdict(list)
        for sheet, fp in items:
            by_sheet[sheet].append(fp)
        for sheet, fps in by_sheet.items():
            t = pcbnew.PCB_TEXT(b)
            t.SetText(f"parked: {sheet}")
            t.SetPosition(pcbnew.VECTOR2I(mm(x0), mm(y)))
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
            t.SetLayer(pcbnew.Cmts_User)
            t.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
            b.Add(t)
            y += 3.0
            x, row_h = x0, 0.0
            for fp in fps:
                put(fp, board, 0, 0, 0, True)       # SMD on the main board's back; THT bodies on the control back
                w, h = size(fp)
                if x + w > x1 + 10:
                    x, y, row_h = x0, y + row_h + 1.5, 0.0
                put(fp, board, 0, 0, 0, True)
                bb = fp.GetBoundingBox(False)
                fp.Move(pcbnew.VECTOR2I(mm(x) - bb.GetLeft(), mm(y) - bb.GetTop()))
                x += w + 1.5
                row_h = max(row_h, h)
            y += row_h + 4.0

    b.BuildConnectivity()
    b.Save(PCB)
    placed = sum(1 for r in comps if r in pos)
    print(f"{len(comps)} footprints: {placed} at decided positions, {len(comps) - placed} parked; "
          f"{len(nets)} nets -> {PCB}")


if __name__ == "__main__":
    main()
