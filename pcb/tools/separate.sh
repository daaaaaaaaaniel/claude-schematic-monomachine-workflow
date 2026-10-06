#!/usr/bin/env bash
# Cut the two boards out of machine-filter/machine-filter.kicad_pcb (KiKit multiboard workflow) and give each its
# own fabrication folder:
#   fab/main/machine-filter-main.kicad_pcb, fab/main/bom.csv, fab/main/bom-jlc.csv
#   fab/control/machine-filter-control.kicad_pcb, fab/control/bom.csv
# Run after tools/build.sh (it needs out/bom.csv). Gerbers, drill files and the CPL are exported from the separated
# boards in a later step (HANDOFF.md, "Next steps"); this script doesn't make them.
#   FAB=<dir>  write somewhere other than pcb/fab
#   PCB=<file> separate another PCB file
set -euo pipefail
PCB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KIKIT="${KIKIT:-/opt/kikit/bin/kikit}"               # setup-toolchain.sh: venv with system site-packages (pcbnew)
FAB="${FAB:-$PCB_DIR/fab}"
SRC="${PCB:-$PCB_DIR/machine-filter/machine-filter.kicad_pcb}"
cd "$PCB_DIR"
if ! "$(dirname "$KIKIT")/python" -c "import wx" 2>/dev/null; then   # no usable wxPython: an empty stand-in
  export PYTHONPATH="$PCB_DIR/tools/wxstub${PYTHONPATH:+:$PYTHONPATH}"
fi
python3 design/pcb_skeleton.py --boxes 2>/dev/null | while read -r board x0 y0 x1 y1; do
  mkdir -p "$FAB/$board"
  "$KIKIT" separate --stripAnnotations \
    -s "type: rectangle; tlx: ${x0}mm; tly: ${y0}mm; brx: ${x1}mm; bry: ${y1}mm" \
    "$SRC" "$FAB/$board/machine-filter-$board.kicad_pcb" 2>&1 | grep -v -e "assert" -e "Debug: " || true
  test -s "$FAB/$board/machine-filter-$board.kicad_pcb" || { echo "kikit separate failed for $board"; exit 1; }
  echo "$board: $FAB/$board/machine-filter-$board.kicad_pcb"
done
rm -f "$FAB"/*/~*.lck
python3 tools/split_bom.py out/bom.csv "$FAB"
