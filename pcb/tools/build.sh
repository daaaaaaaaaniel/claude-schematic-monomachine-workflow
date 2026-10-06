#!/usr/bin/env bash
# Build and check MACHINE FILTER's schematic: one KiCad project (machine-filter/) holding both boards.
# Run from anywhere; needs tools/setup-toolchain.sh done first.
#   0. (FLOORPLAN=1) design/floorplan.py: re-derive the pin assignment -> design/pinmap.py   (~2 min)
#   1. SKiDL netlists from machine_filter.py   -> out/logical.net, out/main.net, out/control.net
#   2. the drawn schematic from gen_sch.py     -> machine-filter/*.kicad_sch (12 pages: overview, main, control)
#   3. KiCad ERC (must report 0)               -> out/erc.rpt
#   4. KiCad netlist of the drawing            -> out/drawn.net
#   5. tools/check_netlist.py: drawing == SKiDL; main + control joined == logical; changes from rev alpha intended
#   6. PDF and the whole-module BOM            -> out/machine-filter.pdf, out/bom.csv (Board, Assembly, DNP columns)
# Per-board fabrication folders (fab/main, fab/control) come from tools/separate.sh once the PCB is laid out.
set -euo pipefail
PCB="$(cd "$(dirname "$0")/.." && pwd)"
SK_PY="${SK_PY:-/opt/sk/bin/python}"                 # SKiDL's venv (setup-toolchain.sh)
export KICAD10_SYMBOL_DIR="${KICAD10_SYMBOL_DIR:-/usr/share/kicad/symbols}"
export KICAD10_FOOTPRINT_DIR="${KICAD10_FOOTPRINT_DIR:-/usr/share/kicad/footprints}"
SCH=machine-filter/machine-filter.kicad_sch
cd "$PCB"
mkdir -p out

if [ "${FLOORPLAN:-0}" = 1 ]; then
  echo "== 0. floorplan"
  python3 design/floorplan.py
fi
echo "== 1. SKiDL netlists"
"$SK_PY" machine_filter.py 2>&1 | grep -E "errors found|mux select" || true
echo "== 2. draw the schematic"
python3 design/gen_sch.py
echo "== 3. ERC"
kicad-cli sch erc "$SCH" -o out/erc.rpt --severity-all >/dev/null
grep -q "ERC messages: 0" out/erc.rpt || { echo "ERC violations: see out/erc.rpt"; exit 1; }
echo "   0 violations"
echo "== 4. netlist of the drawing"
kicad-cli sch export netlist "$SCH" --format kicadsexpr -o out/drawn.net >/dev/null
echo "== 5. checks"
python3 tools/check_netlist.py
echo "== 6. PDF and BOM"
kicad-cli sch export pdf "$SCH" -o out/machine-filter.pdf >/dev/null
kicad-cli sch export bom "$SCH" -o out/bom.csv \
  --fields 'Reference,Value,Footprint,LCSC,MPN,Board,Assembly,${DNP},${QUANTITY}' \
  --labels 'Reference,Value,Footprint,LCSC,MPN,Board,Assembly,DNP,QUANTITY' \
  --group-by 'Value,Footprint,LCSC,Board,${DNP}' >/dev/null      # DNP parts listed, marked DNP
echo "OK: out/machine-filter.pdf, out/bom.csv"
