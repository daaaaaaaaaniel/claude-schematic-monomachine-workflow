#!/usr/bin/env python3
"""Reject a layout candidate that moved a part d has approved (locked).

    python3 pcb/tools/check_locks.py <approved.kicad_pcb> <candidate.kicad_pcb>
    python3 pcb/tools/check_locks.py HEAD [candidate]       # approved = the board as last committed

Approval is per block (a function group in pcb/design/groups.py): pcb/tools/lock_block.py sets KiCad's own
"locked" flag on every footprint of the block, and the commit records it. This script compares position, rotation
and side of every footprint; any locked part that moved, or lost its lock, is a violation (exit 1). It never trusts
the placer or router to have respected the locks. (Adapted from advice d brought from another session, 2026-10-07.)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, "..", "machine-filter", "machine-filter.kicad_pcb"))


def snap(path):
    import pcbnew
    b = pcbnew.LoadBoard(path)
    return {fp.GetReference(): {"pos": (round(pcbnew.ToMM(fp.GetPosition().x), 3),
                                        round(pcbnew.ToMM(fp.GetPosition().y), 3)),
                                "rot": round(fp.GetOrientationDegrees(), 2), "side": fp.GetLayerName(),
                                "locked": fp.IsLocked()}
            for fp in b.GetFootprints()}


def from_git(rev):
    rel = os.path.relpath(PCB, os.path.join(HERE, "..", ".."))
    data = subprocess.run(["git", "show", f"{rev}:{rel}"], capture_output=True, check=True,
                          cwd=os.path.join(HERE, "..", "..")).stdout
    f = tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False)
    f.write(data)
    f.close()
    return f.name


def check(approved, candidate):
    old, new = snap(approved), snap(candidate)
    geom = lambda d: (d["pos"], d["rot"], d["side"])
    moved = sorted(r for r in new if r in old and geom(new[r]) != geom(old[r]))
    bad = sorted(r for r in old if old[r]["locked"] and (r not in new or geom(new[r]) != geom(old[r])
                                                          or not new[r]["locked"]))
    return {"locked": sum(d["locked"] for d in old.values()), "moved": moved, "locked_violations": bad}


def main():
    a = sys.argv[1]
    c = sys.argv[2] if len(sys.argv) > 2 else PCB
    if not a.endswith(".kicad_pcb"):
        a = from_git(a)
    r = check(a, c)
    print(json.dumps(r, indent=1))
    sys.exit(1 if r["locked_violations"] else 0)


if __name__ == "__main__":
    main()
