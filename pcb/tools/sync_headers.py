#!/usr/bin/env python3
"""After connector_search.py --write and build.sh: bring the board-to-board headers onto the live board.

    python3 pcb/tools/sync_headers.py

Deletes every JAn/JBn footprint (their pin counts may have changed), updates the board from the schematic through
Konnect (dry run, then apply with its plan revision), places each pair from out/connector-search.json (JBn on the
main board's front, JAn on the control board's back) and checks that every pin k of JAn and JBn sits at the
computed panel position. Run tools/check_locks.py / DRC afterwards as usual.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from konnect_call import Client  # noqa: E402

BOARD = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))
SCH = os.path.abspath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_sch"))
OUT = os.path.join(HERE, "..", "out")


def main():
    c = Client()
    try:
        refs = [x["reference"] for x in c.call("get_component_list", {"board": BOARD})["components"]
                if x["reference"].startswith(("JA", "JB"))]
        for r in refs:
            c.call("delete_component", {"board": BOARD, "reference": r})
        plan = c.call("update_pcb_from_schematic", {"board": BOARD, "schematic": SCH, "dry_run": True})
        if plan["status"] != "ready":
            sys.exit(f"update not ready: {plan['status']}: {[d['message'] for d in plan['diagnostics']]}")
        done = c.call("update_pcb_from_schematic", {"board": BOARD, "schematic": SCH, "dry_run": False,
                                                    "expected_plan_revision": plan["plan_revision"]})
        print("update:", done["status"], {k: v["applied"] for k, v in done["coverage"].items() if isinstance(v, dict)
                                          and v.get("applied")})
        c.call("save_project", {})
    finally:
        c.close()
    d = json.load(open(os.path.join(OUT, "connector-search.json")))
    for kind, off, side in (("JB", (180, 50), "front"), ("JA", (100, 50), "back")):
        pl = {}
        for n, l in enumerate(d["lines"], 1):
            o = l["origin_" + kind]
            x, y = l["pin1"]
            sx, sy = l["step"]
            pl[f"{kind}{n}"] = {"x": round(o[0] + off[0], 4), "y": round(o[1] + off[1], 4), "rot": l["rot_" + kind],
                                "pads": [[str(k + 1), round(x + off[0] + k * sx, 4), round(y + off[1] + k * sy, 4)]
                                         for k in range(len(l["pins"]))]}
        path = os.path.join(OUT, f"place-{kind}.json")
        json.dump({"board": "main" if kind == "JB" else "control", "side": side, "placements": pl}, open(path, "w"),
                  indent=1)
        r = subprocess.run([sys.executable, os.path.join(HERE, "apply_placement.py"), path], capture_output=True,
                           text=True)
        print(kind, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-500:])
        if r.returncode:
            sys.exit(1)


if __name__ == "__main__":
    main()
