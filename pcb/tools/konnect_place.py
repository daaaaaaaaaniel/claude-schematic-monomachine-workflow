#!/usr/bin/env python3
"""Apply placement steps from design/placement.py to the board open in KiCad, through Konnect.

    python3 tools/konnect_place.py <step name>     # place that step's parts, check pads, draw its traces, save

Parts are set (x, y, rotation) in one undo step, then flipped to the back where asked. Back-side flips follow
KiCad's own flip (Konnect flip_component); if a part's checked pads land on the wrong spot, the step stops
before any trace is drawn. Traces: (ref1, pad1, ref2, pad2 or None = the pad on pad1's net, width, layer),
drawn as Konnect's L-bend pad-to-pad route.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
from konnect_call import Client  # noqa: E402
import placement as P  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))


def kicad(board, x, y):
    dx, dy = P.OFFSET[board]
    return round(x + dx, 4), round(y + dy, 4)


def pad_map(c, ref):
    r = c.call("get_component_pads", {"board": BOARD, "reference": ref})
    return {p["number"]: p for p in r["pads"]}


def common_net(c, r1, r2, want=None):
    """The net two parts share (not GND); `want` picks by substring when they share several."""
    n1 = {p["number"]: p["net"] for p in pad_map(c, r1).values()}
    n2 = {p["number"]: p["net"] for p in pad_map(c, r2).values()}
    nets = (set(n1.values()) & set(n2.values())) - {"GND", ""}
    if want:
        nets = {n for n in nets if want in n}
    net = sorted(nets)[0]
    return net, next(k for k, v in n1.items() if v == net), next(k for k, v in n2.items() if v == net)


def drag(c, step):
    """Move a staged group as one block: the primary to its spot, the others keeping their offsets from it
    (mirrored top-to-bottom when the block goes to the back, as KiCad mirrors a flipped group); then the traces."""
    import groups as G
    prim, rest = {**G.MAIN, **G.CONTROL}[step["drag"]]
    board, tx, ty, rot, side = step["primary"]
    kx, ky = kicad(board, tx, ty)
    got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
    px, py = got[prim]["x"], got[prim]["y"]
    refs = [prim] + rest
    for r in refs:
        c.call("flip_component", {"board": BOARD, "reference": r, "layer": "B.Cu" if side == "back" else "F.Cu"})
    flip = side == "back" and got[prim]["layer"] != "B.Cu"
    after = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
    moves = []
    for r in refs:
        dx, dy = got[r]["x"] - px, got[r]["y"] - py
        moves.append({"reference": r, "x": round(kx + dx, 4), "y": round(ky + (-dy if flip else dy), 4),
                      "rotation": rot if r == prim else after[r]["rotation"]})
    moves += [{"reference": r, "x": kicad(b, x, y)[0], "y": kicad(b, x, y)[1], "rotation": a}
              for r, (b, x, y, a, s) in step.get("extra", {}).items()]
    c.call("set_component_placements", {"board": BOARD, "placements": moves})
    print(f"  moved {len(moves)} parts as one block; {prim} at panel ({tx}, {ty}) on {side}")
    for r1, r2, width, layer in step.get("traces", []):
        net, p1, p2 = common_net(c, r1, r2)
        c.call("route_pad_to_pad", {"board": BOARD, "net_name": net, "ref1": r1, "pad1": p1, "ref2": r2,
                                    "pad2": p2, "width": width, "layer": layer})
        print(f"  trace {r1}.{p1} -> {r2}.{p2} on {net}")
    print("  save:", c.call("save_project", {}))


def pack(c, step):
    """The group as one block, shelf-packed (primary first) from the top-left corner `at` into rows of `width` mm;
    then the traces: ("L", r1, r2) = Konnect's L-bend on their shared net; ("dogleg", r1, r2, x) = three straight
    segments, the middle one vertical at panel x (to pass beside a socket row)."""
    import json as _json
    import groups as G
    prim, rest = {**G.MAIN, **G.CONTROL}[step["pack"]]
    size = _json.load(open(os.path.join(HERE, "..", "out", "fpsize.json")))
    got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
    board, x0, y0, side = step["at"]
    refs = [prim] + rest
    for r in refs:
        c.call("flip_component", {"board": BOARD, "reference": r, "layer": "B.Cu" if side == "back" else "F.Cu"})
    moves, x, y, row_h = [], 0.0, 0.0, 0.0
    for r in refs:
        w, h, ox, oy = size[got[r]["footprint"]]
        rot = step.get("rot", {}).get(r, 0)
        if rot in (90, 270):
            w, h, ox, oy = h, w, oy, ox
        if side == "back":                          # KiCad mirrors a back-side part top-to-bottom
            oy = -oy
        if x > 0 and x + w > step["width"]:
            x, y, row_h = 0.0, y + row_h + 1.5, 0.0
        kx, ky = kicad(board, x0 + x + w / 2, y0 + y + h / 2)
        moves.append({"reference": r, "x": round(kx - ox, 4), "y": round(ky - oy, 4), "rotation": rot})
        x, row_h = x + w + 1.5, max(row_h, h)
    c.call("set_component_placements", {"board": BOARD, "placements": moves})
    print(f"  {step['pack']}: {len(refs)} parts as one block, {step['width']:.0f} x {y + row_h:.0f} mm "
          f"from panel ({x0}, {y0}) on {side}")
    for tr in step.get("traces", []):
        kind, r1, r2 = tr[:3]
        net, p1, p2 = common_net(c, r1, r2, tr[4] if len(tr) > 4 else None)
        if kind == "L":
            c.call("route_pad_to_pad", {"board": BOARD, "net_name": net, "ref1": r1, "pad1": p1, "ref2": r2,
                                        "pad2": p2, "width": 0.25, "layer": "B.Cu"})
        else:
            a, b = pad_map(c, r1)[p1], pad_map(c, r2)[p2]
            xm = kicad(board, tr[3], 0)[0]
            for (xa, ya, xb, yb) in ((a["x"], a["y"], xm, a["y"]), (xm, a["y"], xm, b["y"]), (xm, b["y"], b["x"], b["y"])):
                if (xa, ya) != (xb, yb):
                    c.call("route_trace", {"board": BOARD, "net_name": net, "layer": "B.Cu", "width": 0.25,
                                           "x1": xa, "y1": ya, "x2": xb, "y2": yb})
        print(f"  trace ({kind}) {r1}.{p1} -> {r2}.{p2} on {net}")
    print("  save:", c.call("save_project", {}))


def main():
    step = next(s for s in P.STEPS if s["name"] == sys.argv[1])
    c = Client()
    try:
        if "drag" in step:                          # d: the whole staged group in one gesture
            drag(c, step)
            return
        if "pack" in step:                          # the group as one block, packed to fit its corner
            pack(c, step)
            return
        moves = []
        for ref, (board, x, y, rot, side) in step["parts"].items():
            kx, ky = kicad(board, x, y)
            moves.append({"reference": ref, "x": kx, "y": ky, "rotation": rot})
        for ref, (board, x, y, rot, side) in step["parts"].items():      # side first: rotation is then KiCad's
            c.call("flip_component", {"board": BOARD, "reference": ref,     # on the final side, so re-runs agree
                                      "layer": "B.Cu" if side == "back" else "F.Cu"})
        c.call("set_component_placements", {"board": BOARD, "placements": moves})
        got = {x["reference"]: x for x in c.call("get_component_list", {"board": BOARD})["components"]}
        for ref in step["parts"]:
            g = got[ref]
            print(f"  {ref}: ({g['x']:.3f}, {g['y']:.3f}) rot {g['rotation']:.0f} on {g['layer']}")
        bad = []
        for (ref, num), (x, y) in step.get("check_pads", {}).items():
            board = step["parts"][ref][0]
            kx, ky = kicad(board, x, y)
            p = pad_map(c, ref)[num]
            px, py = p["x"], p["y"]
            ok = math.hypot(px - kx, py - ky) < 0.05
            print(f"  pad {ref}.{num}: at ({px:.3f}, {py:.3f}), expected ({kx:.3f}, {ky:.3f}) {'ok' if ok else 'WRONG'}")
            if not ok:
                bad.append((ref, num))
        if bad:
            raise SystemExit(f"pads off: {bad}; no traces drawn, board not saved")
        for ref1, pad1, ref2, pad2, width, layer in step.get("traces", []):
            p1 = pad_map(c, ref1)[pad1]
            net = p1["net"]
            if pad2 is None:
                pad2 = next(n for n, p in pad_map(c, ref2).items() if p["net"] == net)
            r = c.call("route_pad_to_pad", {"board": BOARD, "net_name": net, "ref1": ref1, "pad1": pad1,
                                            "ref2": ref2, "pad2": pad2, "width": width, "layer": layer})
            print(f"  trace {ref1}.{pad1} -> {ref2}.{pad2} on {net}, {width} mm, {layer}:",
                  {k: v for k, v in r.items() if k in ("segments", "length_mm", "status", "source")}
                  if isinstance(r, dict) else r)
        print("  save:", c.call("save_project", {}))
    finally:
        c.close()


if __name__ == "__main__":
    main()
