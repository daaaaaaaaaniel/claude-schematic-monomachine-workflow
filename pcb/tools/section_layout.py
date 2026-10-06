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
P = 0.85                      # 0603 pad offset from its centre
ROW = 2.05                    # row pitch


def pin(w, ref, num):
    f = w.fps[ref]
    p = next(q for q in f.Pads() if q.GetNumber() == num)
    return A.mm(p.GetPosition().x) - OX, A.mm(p.GetPosition().y) - OY


def cy_edge(w, ref, side):
    x, y, s = w.placed[ref]
    c = s.cy
    return {"top": y + c[1] - OY, "bottom": y + c[3] - OY, "left": x + c[0] - OX, "right": x + c[2] - OX}[side]


def cv_top(w, chip, minus, out_dir, parts, extra_r_in=None):
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
    for k, ref in enumerate(r_in):                     # pad 2 = the - side (bottom), pad 1 = toward the jack
        res.append((ref, mx, top - k * (3.25 + 0.5), 270))
    return res


def cv_bottom(w, chip, minus, out_dir, parts):
    """The mirror of cv_top for a section on the chip's bottom pin row, facing down (+y)."""
    mx, my = pin(w, chip, minus)
    r1 = cy_edge(w, chip, "bottom") + 0.5 + 0.775
    rows = [r1 + k * ROW for k in range(3)]
    res = []
    for (ref, side), ry in zip(parts[:3], rows):
        d = out_dir if side == "out" else -out_dir
        res.append((ref, mx + d * P, ry, 180 if d < 0 else 0))
    bottom = rows[2] + 0.775 + 0.5 + 1.625
    for k, ref in enumerate(parts[3:]):                 # pad 2 = the - side (top), pad 1 = toward the jack
        res.append((ref, mx, bottom + k * (3.25 + 0.5), 90))
    return res


def layout(w, section):
    if section == "u2_bottom":
        c = cv_bottom(w, "U2", "9", +1, [("R23", "out"), ("C13", "out"), ("R24", "vref"), "R22"])
        d = cv_bottom(w, "U2", "13", -1, [("C14", "out"), ("R28", "vref"), ("R27", "out"), "R26"])
        return c + d
    if section == "u2_top":
        a = cv_top(w, "U2", "2", -1, [("C10", "out"), ("R12", "vref"), ("R11", "out"), "R13", "R10"])
        b = cv_top(w, "U2", "6", +1, [("R19", "out"), ("C12", "out"), ("R20", "vref"), "R18"])
        return a + b
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


def legalise(w, ref, x, y, rot):
    s = w.shape(ref, rot, True)
    kx, ky = x + OX, y + OY
    if w.legal(ref, kx, ky, s):
        return kx, ky, s, 0.0
    best = None
    for r in [k * 0.05 for k in range(1, 61)] + [3.0 + k * 0.25 for k in range(1, 25)]:
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
    w = A.World(A.BOARD, "main")
    plan = []
    for s in secs:
        plan += layout(w, s)
    for ref, *_ in plan:                               # these get re-placed: free them first
        w.placed.pop(ref, None)
    w.rebuild()
    result = {}
    for ref, x, y, rot in plan:
        got = legalise(w, ref, x, y, rot)
        if got is None:
            print(f"{ref}: no legal spot within 9 mm of its pattern position")
            continue
        kx, ky, s, moved = got
        w.placed[ref] = (kx, ky, s)
        w.rebuild()
        result[ref] = {"x": round(kx, 4), "y": round(ky, 4), "rot": rot,
                       "pads": [[p[0], round(kx + p[2], 4), round(ky + p[3], 4)] for p in s.pads]}
        print(f"{ref}: panel ({kx - OX:.2f}, {ky - OY:.2f}) rot {rot}" + (f"  (moved {moved:.2f} mm to clear)" if moved else ""))
    json.dump({"board": "main", "side": "back", "placements": result}, open(out, "w"), indent=1)
    print("written", out)


if __name__ == "__main__":
    main()
