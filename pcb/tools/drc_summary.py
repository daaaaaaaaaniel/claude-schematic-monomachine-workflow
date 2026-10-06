#!/usr/bin/env python3
"""DRC of the saved board, sorted for d's routing rule: problems vs clashes with untraced minor-part pads
(resistor/capacitor pads with no trace on them are ignored while routing; those parts move later)."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design"))
import groups as G
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "machine-filter", "machine-filter.kicad_pcb")
COSMETIC = {"silk_over_copper", "silk_overlap", "lib_footprint_mismatch", "silk_edge_clearance"}
SECONDARY = {r for v in G.SECONDARY.values() for r in v}
TRACED = set(sys.argv[1:])              # "R52.2" etc.: minor-part pads that do have a trace
out = "/tmp/drc_summary.json"
subprocess.run(["kicad-cli", "pcb", "drc", PCB, "--format", "json", "-o", out], capture_output=True)
v = [x for x in json.load(open(out))["violations"] if x["type"] not in COSMETIC]
def ignored_pad(desc):
    m = re.search(r"Pad (\S+) .* of ([RC]\d+)", desc)
    return bool(m) and m.group(2) not in SECONDARY and f"{m.group(2)}.{m.group(1)}" not in TRACED
real = [x for x in v if not any(ignored_pad(i["description"]) for i in x["items"])]
print(f"DRC: {len(real)} problems; {len(v) - len(real)} clashes with untraced minor-part pads (ignored)")
for x in real:
    print("  ", x["type"], [i["description"][:70] for i in x["items"]])
