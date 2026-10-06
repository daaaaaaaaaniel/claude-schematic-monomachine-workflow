#!/usr/bin/env python3
"""One routing experiment with Freerouting on one board, measured before anything touches the real board.

    python3 pcb/tools/route_board.py main|control <name> [--gnd skip|route] [--passes N] [--fr "freerouting args"] [--apply]

1. Cuts the board out of the saved project file into explore/routing/<name>/ (pcbnew, a scratch copy).
2. Exports KiCad's own Specctra DSN and adds d's rules for the router (2026-10-06/07): 90-degree routing only
   (snap_angle ninety_degree), front horizontal / back vertical (layer_rule preferred directions). Freerouting 2.3
   honours the snap angle but ignores the direction costs (from the DSN, the CLI and freerouting.json alike, tested
   2026-10-07); its built-in default already prefers F.Cu horizontal / B.Cu vertical, more weakly than d's rule.
   Hand-routed traces are locked, so they go in as fixed wires.
   --gnd skip (default) leaves ground unrouted for the copper fill; --gnd route lets the router draw it too.
3. Runs Freerouting headless (the local jar; nothing leaves the machine) and imports its session into the scratch
   copy.
4. Measures the scratch copy: DRC problems, unrouted connections (ground counted separately), vias, track length,
   diagonal segments, long off-convention segments.
--apply copies the router's new tracks and vias onto the live board through kicad-python, then saves.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402

BOARD = os.path.join(ROOT, "pcb", "machine-filter", "machine-filter.kicad_pcb")
JAR = "/opt/freerouting/freerouting.jar"
AREA = {"main": (180.4, 64.0, 250.4, 164.0), "control": (100.4, 60.75, 170.4, 167.75)}
GROUND = {"main": "GND", "control": "CTL_GND"}
STUB_MM = 2.5
COSMETIC = {"silk_overlap", "silk_over_copper", "lib_footprint_mismatch", "lib_footprint_issues",
            "silk_edge_clearance", "text_height", "text_thickness"}


def cut(board, out):
    b = pcbnew.LoadBoard(BOARD)
    x0, y0, x1, y1 = AREA[board]

    def inside(p):
        return x0 - 0.5 <= pcbnew.ToMM(p.x) <= x1 + 0.5 and y0 - 0.5 <= pcbnew.ToMM(p.y) <= y1 + 0.5
    gone = ([f for f in b.GetFootprints() if not inside(f.GetPosition())]
            + [t for t in b.GetTracks() if not inside(t.GetStart())]
            + [d for d in b.GetDrawings() if not inside(d.GetBoundingBox().GetCenter())]
            + [z for z in b.Zones() if not inside(z.GetBoundingBox().GetCenter())])
    for it in gone:
        b.Delete(it)
    pcbnew.SaveBoard(out, b)
    return b


def remove_net(dsn, net):
    """Drop a net from the DSN's network and class lists: the router leaves it alone (its pads stay obstacles)."""
    m = re.search(r"\n    \(net " + re.escape(net) + r"\n.*?\n    \)", dsn, flags=re.S)
    if m:
        dsn = dsn[:m.start()] + dsn[m.end():]
    return re.sub(r"(?<=[\s(])" + re.escape(net) + r"(?=[\s)])", "", dsn) if False else \
        re.sub(r"(\(class [^\n]*?|\n {6}[^\n(]*?)(?<![\w+-])" + re.escape(net) + r"(?![\w+-])", r"\1", dsn)


def rules(dsn, against):
    add = (f"    (snap_angle ninety_degree)\n"
           f"    (autoroute_settings\n      (fanout off)\n      (autoroute on)\n      (postroute on)\n"
           f"      (vias on)\n      (via_costs 50)\n      (plane_via_costs 5)\n      (start_ripup_costs 100)\n"
           f"      (start_pass_no 1)\n"
           f"      (layer_rule F.Cu\n        (active on)\n        (preferred_direction horizontal)\n"
           f"        (preferred_direction_trace_costs 1.0)\n        (against_preferred_direction_trace_costs {against})\n      )\n"
           f"      (layer_rule B.Cu\n        (active on)\n        (preferred_direction vertical)\n"
           f"        (preferred_direction_trace_costs 1.0)\n        (against_preferred_direction_trace_costs {against})\n      )\n"
           f"    )\n")
    i = dsn.index("  (placement")
    j = dsn.rindex("  )", 0, i)                      # the end of (structure ...)
    return dsn[:j] + add + dsn[j:]


def measure(pcb, board, gnd):
    out = pcb + ".drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", pcb, "--format", "json", "-o", out], capture_output=True)
    d = json.load(open(out))
    real = [v for v in d["violations"] if v["type"] not in COSMETIC]
    unc = d.get("unconnected_items", [])
    gn = GROUND[board]
    g_unc = [u for u in unc if any(f"[{gn}]" in i["description"] for i in u["items"])]
    b = pcbnew.LoadBoard(pcb)
    tr = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]

    def off(t):
        s, e, layer = t.GetStart(), t.GetEnd(), t.GetLayerName()
        return (layer == "B.Cu" and s.y == e.y and s.x != e.x) or (layer == "F.Cu" and s.x == e.x and s.y != e.y)
    return {"drc_problems": len(real), "drc_types": sorted({v["type"] for v in real}),
            "unrouted": len(unc) - len(g_unc), "unrouted_ground": len(g_unc),
            "vias": sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"),
            "track_mm": round(sum(pcbnew.ToMM(t.GetLength()) for t in tr), 1),
            "diagonal_segments": sum(1 for t in tr if t.GetStart().x != t.GetEnd().x and t.GetStart().y != t.GetEnd().y),
            "off_convention_long": sum(1 for t in tr if off(t) and pcbnew.ToMM(t.GetLength()) > STUB_MM)}


def key(t):
    if t.GetClass() == "PCB_VIA":
        return ("via", t.GetPosition().x, t.GetPosition().y, t.GetNetname())
    a, b = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    return ("track", t.GetLayerName(), min(a, b), max(a, b), t.GetWidth(), t.GetNetname())


def apply(routed):
    from kipy import KiCad
    from kipy.board_types import BoardLayer, Track, Via
    from kipy.geometry import Vector2
    live = KiCad(socket_path="ipc:///tmp/kicad/api.sock").get_board()
    have = {}
    for t in live.get_tracks():
        a, b = (t.start.x, t.start.y), (t.end.x, t.end.y)
        have[("track", "F.Cu" if t.layer == BoardLayer.BL_F_Cu else "B.Cu", min(a, b), max(a, b), t.width,
              t.net.name)] = 1
    for v in live.get_vias():
        have[("via", v.position.x, v.position.y, v.net.name)] = 1
    nets = {}
    for t in live.get_tracks() + live.get_vias():
        nets.setdefault(t.net.name, t.net)
    for f in live.get_footprints():
        for p in f.definition.pads:
            nets.setdefault(p.net.name, p.net)
    b = pcbnew.LoadBoard(routed)
    new = []
    for t in b.GetTracks():
        k = key(t)
        if k in have:
            continue
        if t.GetClass() == "PCB_VIA":
            v = Via()
            v.position = Vector2.from_xy(t.GetPosition().x, t.GetPosition().y)
            v.diameter = t.GetWidth(pcbnew.F_Cu)
            v.drill_diameter = t.GetDrillValue()
            v.net = nets[t.GetNetname()]
            new.append(v)
        else:
            n = Track()
            n.start = Vector2.from_xy(t.GetStart().x, t.GetStart().y)
            n.end = Vector2.from_xy(t.GetEnd().x, t.GetEnd().y)
            n.width = t.GetWidth()
            n.layer = BoardLayer.BL_F_Cu if t.GetLayerName() == "F.Cu" else BoardLayer.BL_B_Cu
            n.net = nets[t.GetNetname()]
            new.append(n)
    cm = live.begin_commit()
    live.create_items(new)
    live.push_commit(cm, f"Autorouted ({os.path.basename(os.path.dirname(routed))})")
    live.save()
    print(f"applied {len(new)} new tracks/vias to the live board")


def main():
    board, name = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    gnd = args[args.index("--gnd") + 1] if "--gnd" in args else "skip"
    passes = args[args.index("--passes") + 1] if "--passes" in args else "100"
    against = args[args.index("--against") + 1] if "--against" in args else "4.0"
    d = os.path.join(ROOT, "explore", "routing", name)
    os.makedirs(d, exist_ok=True)
    pcb, dsn, ses = (os.path.join(d, f"{board}.{e}") for e in ("kicad_pcb", "dsn", "ses"))
    if "--apply" in args:
        apply(os.path.join(d, f"{board}-routed.kicad_pcb"))
        return
    b = cut(board, pcb)
    assert pcbnew.ExportSpecctraDSN(b, dsn)
    text = open(dsn).read()
    if gnd == "skip":
        text = remove_net(text, GROUND[board])
    text = rules(text, against)
    open(dsn, "w").write(text)
    if os.path.exists(ses):
        os.remove(ses)
    t0 = time.time()
    extra = args[args.index("--fr") + 1].split() if "--fr" in args else []
    r = subprocess.run(["java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", passes, "--gui.enabled=false"] + extra,
                       capture_output=True, text=True, timeout=3600)
    open(os.path.join(d, "freerouting.log"), "w").write(r.stdout + r.stderr)
    if not os.path.exists(ses):
        sys.exit(f"no session written; see {d}/freerouting.log")
    b = pcbnew.LoadBoard(pcb)
    assert pcbnew.ImportSpecctraSES(b, ses)
    routed = os.path.join(d, f"{board}-routed.kicad_pcb")
    pcbnew.SaveBoard(routed, b)
    m = measure(routed, board, gnd)
    m.update({"board": board, "gnd": gnd, "passes": passes, "against": against, "seconds": round(time.time() - t0)})
    json.dump(m, open(os.path.join(d, "metrics.json"), "w"), indent=1)
    print(json.dumps(m))


if __name__ == "__main__":
    main()
