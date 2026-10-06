#!/usr/bin/env python3
"""Re-match swap groups to the placed board (pin map follows the layout; groups in design/swap_groups.py).

    python3 pcb/tools/rematch.py headers [--board X.kicad_pcb] [--write]   # board-to-board header pin order
    python3 pcb/tools/rematch.py adc [--write]                             # ADC pins (tools/rematch_adc.py)

headers: for each header pair JAn/JBn on the board, every signal is tried at every non-ground pin (all orders, by
brute force: at most 8 signals per header). The cost of a signal at a pin is the orthogonal (|dx| + |dy|) distance
from that pin to the nearest placed pad of the signal on the main board, plus the same to its CTL_ twin on the control
board. Rules from swap_groups.board_headers: ground pins keep their places; neighbours with no ground between them
must be of one kind (audio, CV, pot, digital); a supply pin has only grounds beside it (no +12 V next to -12 V). Pads of parts not yet
on a board don't count (the tool says which signals had no target). JAn pin k must sit on JBn pin k (same panel
position, the boards stack); a pair that doesn't is reported and skipped.

--write puts the new order into design/pinmap.py HEADER_PINS. Then: delete any trace on a header pad whose net
changes, pcb/tools/build.sh, update the PCB from the schematic (Konnect dry run, then apply), and paste
python3 pcb/tools/doc_tables.py into docs/placement-guide.md. Header pins carry no firmware meaning.
"""
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import pinmap as PM  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
PINMAP = os.path.join(HERE, "..", "design", "pinmap.py")
OFFSET = {"main": (180.0, 50.0), "control": (100.0, 50.0)}       # KiCad = panel + offset (design/pcb_skeleton.py)
AREA = {"main": (180.0, 64.0, 250.0, 164.0), "control": (100.0, 60.7, 170.0, 167.8)}   # outlines, KiCad mm
SUPPLY = {"+12V", "-12V", "+3V3_A"}
BAD_NEIGHBOURS = 1000.0       # mm-equivalent penalty: two kinds side by side without a ground between them


def kind(net):
    if net in SUPPLY:
        return "supply"
    if net.startswith("CV_"):
        return "cv"
    if net.startswith("POT_"):
        return "pot"
    if net in ("IN_L", "IN_R", "OUT_L", "OUT_R"):
        return "audio"
    return "digital"                                           # MUX_A/B/C, LED_A


def on(board, x, y):
    x0, y0, x1, y1 = AREA[board]
    return x0 <= x <= x1 and y0 <= y <= y1


def read_board(path):
    import pcbnew
    b = pcbnew.LoadBoard(path)
    pads = []                                                  # (ref, pad, net, board, panel x, panel y)
    for f in b.GetFootprints():
        for p in f.Pads():
            x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
            board = "main" if on("main", x, y) else "control" if on("control", x, y) else None
            if board:
                ox, oy = OFFSET[board]
                pads.append((f.GetReference(), p.GetNumber(), p.GetNetname(), board, x - ox, y - oy))
    return pads


def best_order(sigs, slots, cost):
    """sigs: the header's signals; slots: its pin list with 'GND' fixed and None where a signal goes."""
    free = [k for k, s in enumerate(slots) if s is None]
    best = (float("inf"), None)
    for perm in itertools.permutations(sigs):
        order = list(slots)
        for k, s in zip(free, perm):
            order[k] = s
        c = sum(cost[s][k] for k, s in zip(free, perm))
        for k in range(len(order) - 1):
            a, b = order[k], order[k + 1]
            if a != "GND" and b != "GND":
                if a in SUPPLY or b in SUPPLY:
                    c = float("inf")                           # a supply pin sits between grounds, alone
                elif kind(a) != kind(b):
                    c += BAD_NEIGHBOURS
        for k, s in enumerate(order):
            if s in SUPPLY and "GND" not in order[max(0, k - 1):k + 2]:
                c = float("inf")
        if c < best[0]:
            best = (c, order)
    return best


def headers(path, write):
    pads = read_board(path)
    by_net = {}
    for ref, num, net, board, x, y in pads:
        if not ref.startswith(("JA", "JB")):
            by_net.setdefault((board, net), []).append((x, y))
    new_pins, report = {}, []
    for h, old in sorted(PM.HEADER_PINS.items()):
        jb = {num: (x, y) for ref, num, net, board, x, y in pads if ref == f"JB{h}" and board == "main"}
        ja = {num: (x, y) for ref, num, net, board, x, y in pads if ref == f"JA{h}" and board == "control"}
        if len(jb) != len(old) or len(ja) != len(old):
            report.append(f"JA{h}/JB{h}: not both on their boards yet; order kept")
            continue
        off = [k for k in jb if max(abs(jb[k][0] - ja[k][0]), abs(jb[k][1] - ja[k][1])) > 0.01]
        if off:
            report.append(f"JA{h}/JB{h}: pins {sorted(off, key=int)} don't line up between the boards; order kept")
            continue
        pos = [jb[str(k + 1)] for k in range(len(old))]
        sigs = [s for s in old if s != "GND"]
        missing = []
        cost = {}
        for s in sigs:
            row = []
            for x, y in pos:
                c = 0.0
                for board, net in (("main", s), ("control", "CTL_" + s)):
                    t = by_net.get((board, net))
                    if t:
                        c += min(abs(x - tx) + abs(y - ty) for tx, ty in t)
                    else:
                        missing.append(f"{net} ({board})")
                row.append(c)
            cost[s] = row
        slots = [s if s == "GND" else None for s in old]
        before = sum(cost[s][k] for k, s in enumerate(old) if s != "GND")
        c, order = best_order(sigs, slots, cost)
        after = sum(cost[s][k] for k, s in enumerate(order) if s != "GND")
        new_pins[h] = order
        report.append(f"JA{h}/JB{h}: {before:.1f} -> {after:.1f} mm (orthogonal, both boards)"
                      + ("" if order != old else ", unchanged"))
        for k, (a, b) in enumerate(zip(old, order)):
            if a != b:
                report.append(f"    pin {k + 1}: {a} -> {b}")
        if missing:
            report.append(f"    no placed target yet for: {', '.join(sorted(set(missing)))}")
    print("\n".join(report))
    if write and new_pins:
        pins = {h: new_pins.get(h, old) for h, old in PM.HEADER_PINS.items()}
        t = open(PINMAP).read()
        t = re.sub(r"^HEADER_PINS = .*$", "HEADER_PINS = " + repr(pins), t, count=1, flags=re.M)
        open(PINMAP, "w").write(t)
        print("written to design/pinmap.py HEADER_PINS")


def main():
    args = sys.argv[1:]
    path = args[args.index("--board") + 1] if "--board" in args else BOARD
    if not args or args[0] not in ("headers", "adc"):
        sys.exit(__doc__)
    if args[0] == "headers":
        headers(path, "--write" in args)
    else:
        import rematch_adc
        rematch_adc.main()


if __name__ == "__main__":
    main()
