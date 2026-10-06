#!/usr/bin/env python3
"""Measure the saved board as a layout candidate and keep it, so placement/routing changes are compared on the
full set of measurements, not on one number (adapted from Keitark/pcba-design-skills, pcb-layout-review, MIT).

    python3 tools/score_candidate.py <name> ["what changed"]

Writes explore/candidates/<name>/ with a copy of the board file and metrics.json, and prints the comparison with the
best accepted candidate (explore/candidates/best.txt). A candidate that moved a part locked in the best candidate (an
approved block, see check_locks.py) is rejected outright. Otherwise it is better only if it adds no unrouted connection,
real DRC problem or power disconnect, and improves at least one of them (or, when those tie, vias or track length).
Promote it with --accept.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, HERE)
import drc_summary as D  # noqa: E402
import pcbnew  # noqa: E402

CAND = os.path.join(ROOT, "explore", "candidates")
POWER = re.compile(r"^(GND|\+12V|-12V|\+3V3_A|\+3V3_D|VIN|-10V_REF|CTL_.*)$")


def measure():
    out = "/tmp/score_drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", D.PCB, "--format", "json", "-o", out], capture_output=True)
    d = json.load(open(out))
    traced = D.traced_parts()
    absent = lambda r: bool(re.fullmatch(r"[RC]\d+", r)) and r not in D.SECONDARY and r not in traced
    v = [x for x in d["violations"] if x["type"] not in D.COSMETIC]
    refs = lambda x: set(re.findall(r"\bof ([A-Z]+\d+)\b", " ".join(i["description"] for i in x["items"])))
    real = [x for x in v if not any(absent(r) for r in refs(x))]
    unc = d.get("unconnected_items", [])
    placed_unc = [x for x in unc if not any(absent(r) for r in refs(x))]
    power_unc = [x for x in placed_unc if any(POWER.match(m) for i in x["items"]
                                              for m in re.findall(r"\[([^\]]+)\]", i["description"]))]
    b = pcbnew.LoadBoard(D.PCB)
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    return {"unrouted_between_placed_parts": len(placed_unc), "power_disconnects": len(power_unc),
            "drc_problems": len(real), "vias": sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"),
            "track_mm": round(sum(pcbnew.ToMM(t.GetLength()) for t in tracks), 1),
            "parts_on_main_board": sum(1 for f in b.GetFootprints() if 180 <= pcbnew.ToMM(f.GetPosition().x) <= 251),
            "diagonal_segments": sum(1 for t in tracks if t.GetStart().x != t.GetEnd().x and t.GetStart().y != t.GetEnd().y)}


def better(new, old):
    hard = ("unrouted_between_placed_parts", "drc_problems", "power_disconnects")
    if any(new[k] > old[k] for k in hard):
        return False
    if any(new[k] < old[k] for k in hard):
        return True
    return (new["vias"], new["track_mm"]) < (old["vias"], old["track_mm"])


def main():
    name = sys.argv[1]
    note = next((a for a in sys.argv[2:] if not a.startswith("--")), "")
    m = measure()
    os.makedirs(os.path.join(CAND, name), exist_ok=True)
    shutil.copy(D.PCB, os.path.join(CAND, name, "machine-filter.kicad_pcb"))
    json.dump({"name": name, "note": note, "metrics": m}, open(os.path.join(CAND, name, "metrics.json"), "w"), indent=1)
    best_file = os.path.join(CAND, "best.txt")
    best = open(best_file).read().strip() if os.path.exists(best_file) else None
    print(f"{name}: {m}")
    if best and best != name:
        bm = json.load(open(os.path.join(CAND, best, "metrics.json")))["metrics"]
        import check_locks
        lk = check_locks.check(os.path.join(CAND, best, "machine-filter.kicad_pcb"), D.PCB)
        m["locked_violations"] = lk["locked_violations"]
        json.dump({"name": name, "note": note, "metrics": m}, open(os.path.join(CAND, name, "metrics.json"), "w"), indent=1)
        verdict = ("REJECTED: moved locked parts " + ", ".join(lk["locked_violations"]) if lk["locked_violations"]
                   else "better" if better(m, bm) else "not better")
        print(f"vs best ({best}): {bm}\n=> {verdict}")
    if m.get("locked_violations"):
        sys.exit(1)
    if "--accept" in sys.argv or not best:
        open(best_file, "w").write(name)
        print(f"best is now {name}")


if __name__ == "__main__":
    main()
