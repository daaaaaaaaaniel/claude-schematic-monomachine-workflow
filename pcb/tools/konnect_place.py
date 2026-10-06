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


def main():
    step = next(s for s in P.STEPS if s["name"] == sys.argv[1])
    c = Client()
    try:
        moves = []
        for ref, (board, x, y, rot, side) in step["parts"].items():
            kx, ky = kicad(board, x, y)
            moves.append({"reference": ref, "x": kx, "y": ky, "rotation": rot})
        c.call("set_component_placements", {"board": BOARD, "placements": moves})
        for ref, (board, x, y, rot, side) in step["parts"].items():
            c.call("flip_component", {"board": BOARD, "reference": ref,
                                      "layer": "B.Cu" if side == "back" else "F.Cu"})
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
