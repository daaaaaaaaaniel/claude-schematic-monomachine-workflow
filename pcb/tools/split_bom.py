"""Split the whole-module BOM (out/bom.csv, from kicad-cli with a Board column) into one BOM per board.

    python3 tools/split_bom.py out/bom.csv fab
writes
    fab/main/bom.csv          every main-board part (JLC-assembled and hand-soldered, with the Assembly column)
    fab/main/bom-jlc.csv      JLC's upload format (Comment, Designator, Footprint, LCSC Part #): Assembly = JLC (SMD),
                              not DNP (to have JLC fit the optional microSD socket J15, clear its DNP flag)
    fab/control/bom.csv       every control-board part (all hand-soldered)
"""
import csv
import os
import sys

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, newline="")))
for board in ("main", "control"):
    os.makedirs(os.path.join(out, board), exist_ok=True)
    mine = [r for r in rows if r["Board"] == board]
    cols = [c for c in rows[0] if c != "Board"]
    with open(os.path.join(out, board, "bom.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(mine)
    if board == "main":
        with open(os.path.join(out, board, "bom-jlc.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for r in mine:
                if r["Assembly"] == "JLC (SMD)" and not r.get("DNP"):
                    w.writerow([r["Value"], r["Reference"], r["Footprint"].split(":")[-1], r["LCSC"]])
    print(f"{board}: {sum(int(r['QUANTITY']) for r in mine)} parts in {len(mine)} lines")
