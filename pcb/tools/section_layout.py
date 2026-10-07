#!/usr/bin/env python3
"""Lay out one section's small parts by a fixed pattern around its op-amp pins, section by section (d, 2026-10-07).

    python3 pcb/tools/section_layout.py <section> [<section> ...] [-o out.json]
    python3 pcb/tools/apply_placement.py out/section-<names>.json

The pattern for an op-amp section (docs/placement-guide.md sections 3-4): a "spine" runs straight out from the
- pin; every part on the - node is a row across the spine with its - pad on it; the feedback pair (R_f, C_f)
reaches from the spine to the output side, the offset resistor to the other side; the input resistor stands
in line at the end of the spine. Rows are 2.05 mm apart (0603 courtyard 1.55 mm + 0.5 mm). Positions come from the
pin coordinates on the saved board; each part is then checked with the placer's rules (tools/auto_place.py) and,
only if it collides, moved to the nearest legal spot (same rotation). Nothing is written to the board here.
Rotations of the 0603 parts on the back: 0 = pad 1 at -x, 90 = pad 1 at +y, 180 = pad 1 at +x, 270 = pad 1 at -y.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auto_place as A  # noqa: E402

OX, OY = 180.0, 50.0          # main board: KiCad = panel + offset
OFF = {"main": (180.0, 50.0), "control": (100.0, 50.0)}


def off(w):
    return OFF[w.board]
P = 0.85                      # 0603 pad offset from its centre
ROW = 2.05                    # row pitch


def pin(w, ref, num):
    f = w.fps[ref]
    p = next(q for q in f.Pads() if q.GetNumber() == num)
    ox, oy = off(w)
    return A.mm(p.GetPosition().x) - ox, A.mm(p.GetPosition().y) - oy


def cy_edge(w, ref, side):
    x, y, s = w.placed[ref]
    c = s.cy
    ox, oy = off(w)
    return {"top": y + c[1] - oy, "bottom": y + c[3] - oy, "left": x + c[0] - ox, "right": x + c[2] - ox}[side]


def cv_top(w, chip, minus, out_dir, parts, rin_row=False):
    """A CV section on the chip's top pin row, facing up (-y). parts: (row1, row2, row3) as (ref, side) with side
    'out' or 'vref'; then the input resistor(s) in line above. out_dir: -1 = output pin to the left, +1 = right."""
    mx, my = pin(w, chip, minus)
    r1 = cy_edge(w, chip, "top") - 0.5 - 0.775
    rows = [r1 - k * ROW for k in range(3)]
    res = []
    for (ref, side), ry in zip(parts[:3], rows):
        d = out_dir if side == "out" else -out_dir
        # pad 1 is the - pad on every part here: put it on the spine
        res.append((ref, mx + d * P, ry, 180 if d < 0 else 0))
    top = rows[2] - 0.775 - 0.5 - 1.625
    r_in = parts[3:]
    if rin_row:                                         # input resistor as a 4th row, pad 2 (-) on the spine
        res.append((r_in[0], mx + out_dir * P, rows[2] - ROW, 0 if out_dir < 0 else 180))
        r_in = r_in[1:]
        top -= ROW
    for k, ref in enumerate(r_in):                     # pad 2 = the - side (bottom), pad 1 = toward the jack
        res.append((ref, mx, top - k * (3.25 + 0.5), 270))
    return res


def cv_bottom(w, chip, minus, out_dir, parts, rin_row=False):
    """The mirror of cv_top for a section on the chip's bottom pin row, facing down (+y)."""
    mx, my = pin(w, chip, minus)
    r1 = cy_edge(w, chip, "bottom") + 0.5 + 0.775
    rows = [r1 + k * ROW for k in range(3)]
    res = []
    for (ref, side), ry in zip(parts[:3], rows):
        d = out_dir if side == "out" else -out_dir
        res.append((ref, mx + d * P, ry, 180 if d < 0 else 0))
    bottom = rows[2] + 0.775 + 0.5 + 1.625
    r_in = parts[3:]
    if rin_row:
        res.append((r_in[0], mx + out_dir * P, rows[2] + ROW, 0 if out_dir < 0 else 180))
        r_in = r_in[1:]
        bottom += ROW
    for k, ref in enumerate(r_in):                      # pad 2 = the - side (top), pad 1 = toward the jack
        res.append((ref, mx, bottom + k * (3.25 + 0.5), 90))
    return res


def layout(w, section):
    if section == "u1_top":
        a = cv_top(w, "U1", "2", -1, [("C11", "out"), ("R16", "vref"), ("R15", "out"), "R17", "R14"], rin_row=True)
        b = cv_top(w, "U1", "6", +1, [("R31", "out"), ("C15", "out"), ("R32", "vref"), "R30"], rin_row=True)
        return a + b
    if section == "u5":                                # U5's series resistor beside the reference's pin 2
        p2 = pin(w, "U5", "2")
        return [("R3", p2[0] - 0.3, p2[1] - 3.2, 90)]   # pad 2 (-12 V) up, pad 1 (-10V_REF) down toward pin 2
    if section == "u1_bottom":
        c = cv_bottom(w, "U1", "9", +1, [("R35", "out"), ("C16", "out"), ("R36", "vref"), "R34"])
        d = cv_bottom(w, "U1", "13", -1, [("C17", "out"), ("R40", "vref"), ("R39", "out"), "R38"])
        return c + d
    if section == "u2_bottom":
        c = cv_bottom(w, "U2", "9", +1, [("R23", "out"), ("C13", "out"), ("R24", "vref"), "R22"], rin_row=True)
        d = cv_bottom(w, "U2", "13", -1, [("C14", "out"), ("R28", "vref"), ("R27", "out"), "R26"], rin_row=True)
        return c + d
    if section == "u2_top":
        a = cv_top(w, "U2", "2", -1, [("C10", "out"), ("R12", "vref"), ("R11", "out"), "R13", "R10"])
        b = cv_top(w, "U2", "6", +1, [("R19", "out"), ("C12", "out"), ("R20", "vref"), "R18"])
        return a + b
    if section == "ctl_u6":  # noqa                           # the mux's decoupler at its supply pin 16
        p16 = pin(w, "U6", "16")
        return [("C80", p16[0] + 1.25, p16[1] - 3.2, 0)]
    if section in ("ctl_u7", "ctl_u8"):
        chip = "U7" if section == "ctl_u7" else "U8"
        dec = {"U7": ("C81", "C82"), "U8": ("C83", "C84")}[chip]
        res = []
        p4, p11 = pin(w, chip, "4"), pin(w, chip, "11")
        res.append((dec[0], p4[0] + 3.4, p4[1], 0))      # +12 V cap at pin 4 (right column), pad 1 nearest
        res.append((dec[1], p11[0] - 3.4, p11[1], 0))    # -12 V cap at pin 11 (left column), pad 2 nearest
        # each section's three resistors as a parallel bank (3.17 mm pitch), leads toward the chip on the side
        # of its pins; sections on the upper half fan upward, the lower half downward
        import pinmap as PM
        names = ["BASE", "WIDTH", "HPRES", "LPRES", "EQF", "EQG", "DIST", "SRR"]
        sect_pins = {1: ("1", "3"), 2: ("7", "5"), 3: ("8", "10"), 4: ("14", "12")}   # out, + of each section
        for i, n in enumerate(names):
            u, k = PM.LED_UNIT[n]
            if u != chip:
                continue
            out_p, plus_p = (pin(w, chip, q) for q in sect_pins[k])
            right = out_p[0] > p11[0] + 1                 # pins on the right column
            side = 1 if right else -1
            up = -1 if k in (1, 4) else 1                 # sections A/D are the upper ones (rot 180)
            x = plus_p[0] + side * (2.9 + 2.54)          # bank centre: inner lead 2.9 mm outside the pin
            for j, ref in enumerate((f"R{90 + i}", f"R{80 + i}", f"R{71 + i}")):
                y = plus_p[1] + up * (1.6 + j * 3.17)
                # + side (R90 pad 1, R80 pad 2) and the feedback side (R71 pad 1) toward the chip
                inner_is_pad1 = ref.startswith(("R9", "R7"))
                rot = (180 if inner_is_pad1 else 0) if right is False else (0 if inner_is_pad1 else 180)
                res.append((ref, x, y, rot))
        return res
    if section == "microsd":  # noqa
        # the five SD pull-ups as a column of rows beside the Seed3 pins they serve (pad 1 = SD line, toward the
        # pin; pad 2 = +3V3_D, a common rail on the left), and J15's decoupler right at its supply pin 4
        sx = cy_edge(w, "A1", "left") - 0.5 - 1.625
        res = [(ref, sx, pin(w, "A1", pnum)[1], 180)
               for ref, pnum in (("R102", "6"), ("R103", "5"), ("R104", "4"), ("R100", "3"), ("R101", "2"))]
        p4 = pin(w, "J15", "4")
        res.append(("C100", p4[0] + 2.8, p4[1], 0))                       # pad 1 (+3V3_D) toward J15 pin 4
        return res
    if section == "u4":
        # section A (bottom row) faces U3: it goes to the right, its - and output traces leaving under the body
        right = cy_edge(w, "U4", "right")
        ym, yo = 40.6, 42.3
        x1 = right + 0.5 + 0.775
        res = [("R61", x1, (ym + yo) / 2, 270), ("C60", x1 + ROW, (ym + yo) / 2, 270),
               ("R62", x1 + ROW, (ym + yo) / 2 - 4.2, 90)]                 # output series R, pad 2 toward J1
        p8 = pin(w, "U4", "8")
        res.append(("C72", x1, p8[1] - 2.0, 270))                          # +12 V pad (1) up, by pin 8
        # section B (top row) faces up: the spine pattern, output pin 7 to the right
        sx, sy = pin(w, "U4", "6")
        r1 = cy_edge(w, "U4", "top") - 0.5 - 0.775
        res += [("R65", sx + P, r1, 0), ("C62", sx + P, r1 - ROW, 0), ("R64", sx - P, r1 - 2 * ROW, 0),
                ("R66", sx + P + 0.85, r1 - 3 * ROW, 0)]
        p4 = pin(w, "U4", "4")
        res.append(("C73", cy_edge(w, "U4", "left") - 0.5 - 0.775, p4[1] - 0.6, 90))   # -12 V pad (2) up, by pin 4
        return res
    if section == "u3":
        sx, sy = pin(w, "U3", "2")                     # section A: bottom row, - pin 2, output pin 1 to the right
        r1 = cy_edge(w, "U3", "bottom") + 0.5 + 0.775
        res = [("R51", sx + P, r1, 0), ("C50", sx + P, r1 + ROW, 0),
               ("R50", sx, r1 + ROW + 0.775 + 0.5 + 1.625, 90)]        # pad 2 (-) on top
        p4 = pin(w, "U3", "4")
        res.append(("C71", p4[0], cy_edge(w, "U3", "bottom") + 0.5 + 1.625, 90))   # -12 V pad (2) at pin 4
        # section B: top row faces U4, so it goes to the left: the - and output traces leave under the chip body
        left = cy_edge(w, "U3", "left")
        ym, yo = 48.3, 50.0                            # the two exits under the body (between pin rows)
        x1 = left - 0.5 - 0.775 - 0.4
        res += [("R55", x1, (ym + yo) / 2, 270), ("C52", x1 - ROW, (ym + yo) / 2, 270),
                ("R54", x1 - ROW - 0.775 - 0.5 - 1.625, ym, 0)]          # pad 2 (-) toward the chip
        p8 = pin(w, "U3", "8")
        right = cy_edge(w, "U3", "right")
        res.append(("C70", right + 0.5 + 0.775, p8[1], 270))              # +12 V pad (1) on top, by pin 8
        p17 = pin(w, "A1", "17")
        res.append(("R56", right + 0.5 + 1.625 + 0.3, p17[1], 0))         # output series R toward Seed pin 17
        return res
    raise SystemExit(f"unknown section {section}")


def legalise(w, ref, x, y, rot, limit=None):
    s = w.shape(ref, rot, True)
    ox, oy = off(w)
    mx = sum(p[2] for p in s.pads) / len(s.pads)        # (x, y) is where the part's pads centre on
    my = sum(p[3] for p in s.pads) / len(s.pads)
    kx, ky = round((x + ox - mx) / 0.05) * 0.05, round((y + oy - my) / 0.05) * 0.05
    if w.legal(ref, kx, ky, s):
        return kx, ky, s, 0.0
    best = None
    radii = [k * 0.05 for k in range(1, 61)] + [3.0 + k * 0.25 for k in range(1, 49)]
    for r in radii[:limit]:
        for i in range(max(8, int(2 * math.pi * r / 0.05))):
            a = 2 * math.pi * i / max(8, int(2 * math.pi * r / 0.05))
            cx, cy = round((kx + r * math.cos(a)) / 0.05) * 0.05, round((ky + r * math.sin(a)) / 0.05) * 0.05
            if w.legal(ref, cx, cy, s):
                best = (cx, cy, s, r)
                break
        if best:
            return best
    return None


def main():
    secs = [a for a in sys.argv[1:] if not a.startswith("-") and not a.endswith(".json")]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else os.path.join(
        HERE, "..", "out", f"section-{'-'.join(secs)}.json")
    board = "control" if all(s.startswith("ctl_") for s in secs) else "main"
    w = A.World(A.BOARD, board)
    OXY = off(w)
    plan = []
    for s in secs:
        plan += layout(w, s)
    for ref, *_ in plan:                               # these get re-placed: free them first
        w.placed.pop(ref, None)
    w.rebuild()
    result = {}
    # first every part that fits on its pattern spot (nudged at most 0.5 mm), then the rest wherever is nearest,
    # so a displaced part never takes another part's pattern spot
    first = []
    for ref, x, y, rot in plan:
        got = legalise(w, ref, x, y, rot, limit=10)
        if got is None:
            first.append(None)
            continue
        kx, ky, s, moved = got
        w.placed[ref] = (kx, ky, s)
        w.rebuild()
        first.append(got)
    for i, ((ref, x, y, rot), got) in enumerate(zip(plan, first)):
        if got is None:
            for r2 in [rot] + [a for a in (0, 90, 180, 270) if a != rot]:   # same turn first, then the others
                got = legalise(w, ref, x, y, r2)
                if got is not None:
                    plan[i] = (ref, x, y, r2)
                    rot = r2
                    break
        if got is None:
            print(f"{ref}: no legal spot within 15 mm of its pattern position")
            continue
        kx, ky, s, moved = got
        if ref not in w.placed:
            w.placed[ref] = (kx, ky, s)
            w.rebuild()
        result[ref] = {"x": round(kx, 4), "y": round(ky, 4), "rot": rot,
                       "pads": [[p[0], round(kx + p[2], 4), round(ky + p[3], 4)] for p in s.pads]}
        print(f"{ref}: panel ({kx - OXY[0]:.2f}, {ky - OXY[1]:.2f}) rot {rot}" + (f"  (moved {moved:.2f} mm to clear)" if moved else ""))
    json.dump({"board": board, "side": "back", "placements": result}, open(out, "w"), indent=1)
    print("written", out)


if __name__ == "__main__":
    main()
