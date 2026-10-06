#!/usr/bin/env python3
"""DRC of the saved board, sorted by d's rule (2026-10-06): a minor part (a resistor or capacitor that is not a
secondary part, groups.SECONDARY) counts as absent until one of its pads has a trace. Clashes involving such a part
(its pads or its courtyard) are listed as ignored; everything else is a problem.

    python3 tools/drc_summary.py

"Has a trace" is read from the saved board (read-only, pcbnew): a track end lies on one of the part's pads.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import groups as G  # noqa: E402
import pcbnew  # noqa: E402

PCB = os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb")
COSMETIC = {"silk_over_copper", "silk_overlap", "lib_footprint_mismatch", "silk_edge_clearance"}
SECONDARY = {r for v in G.SECONDARY.values() for r in v}


def traced_parts():
    b = pcbnew.LoadBoard(PCB)
    ends = []                                   # (point, net): only a track on the pad's own net is a connection
    for t in b.GetTracks():
        pts = [t.GetStart(), t.GetEnd()] if t.GetClass() == "PCB_TRACK" else [t.GetPosition()]
        ends += [(p, t.GetNetname()) for p in pts]
    out = set()
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if any(n == pad.GetNetname() and pad.HitTest(p) for p, n in ends):
                out.add(fp.GetReference())
    return out


def main():
    traced = traced_parts()
    absent = lambda ref: bool(re.fullmatch(r"[RC]\d+", ref)) and ref not in SECONDARY and ref not in traced
    out = "/tmp/drc_summary.json"
    subprocess.run(["kicad-cli", "pcb", "drc", PCB, "--format", "json", "-o", out], capture_output=True)
    v = [x for x in json.load(open(out))["violations"] if x["type"] not in COSMETIC]

    def refs(x):
        r = set()
        for i in x["items"]:
            r |= set(re.findall(r"\bof ([RC]\d+)\b", i["description"]))
            r |= set(re.findall(r"^Footprint ([RC]\d+)\b", i["description"]))
        return r
    real = [x for x in v if not any(absent(r) for r in refs(x))]
    print(f"DRC: {len(real)} problems; {len(v) - len(real)} clashes with untraced minor parts (ignored)")
    for x in real:
        print("  ", x["type"], [i["description"][:70] for i in x["items"]])


if __name__ == "__main__":
    main()
