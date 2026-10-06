# Board-to-board header candidates (2026-10-06, open decision)

The schematic in `pcb/machine-filter/` is built from candidate **A** (`pcb/design/pinmap.py` = `A/pinmap.py`).
The other candidates are kept here so any of them can become the design: copy its `pinmap.py` to
`pcb/design/pinmap.py` and run `pcb/tools/build.sh` (no `FLOORPLAN=1`), then update the docs from
`python3 pcb/tools/doc_tables.py`.

Each `floorplan-crossing.png` shows both boards from the panel side; every line is one board-to-board signal from
its end to its header pin, coloured by group; grey header pins are GND. `floorplan-report.json` lists every line's
length (straight-line mm, not routed length).

## How they were made

- **A**: the first header search (`A/headers-grouped-first.py`): candidate groupings (four natural groups, their
  3-group merges, k-means k = 3 and 4), one header per group with a fixed pin pattern. The winner was a k-means
  grouping. Seed3 USB end at the bottom edge (an assumption, since dropped).
- **B, C, D**: the row search (`pcb/design/headers.py`): signals paired within their kind, legal straight rows,
  pairs placed along the rows by minimum weighted length. B allows 2-4 headers, C 3-4, D exactly 4. Seed3 USB end
  at the bottom edge.
- **A2, B2, C2**: the same three searches with d's USB rule: the Seed3's USB socket at least 25 mm inside the control
  board's edge, the plug's path kept free of tall parts (`USB_MIN`, `PLUG_W` in `floorplan.py`). This is the
  current `floorplan.py`.

## Trace lengths by importance (mm: total, longest single line in brackets)

Weights are what one mm counts in the search (`W_*` in `floorplan.py`, `W_SIG`).

| Tier (weight) | A | B | C | D | A2 | B2 | C2 |
|---|---|---|---|---|---|---|---|
| 1V/OCT op-amp out → ADC (6) | 12 (9) | 12 (9) | 7 (4) | 12 (9) | 7 (3) | 7 (3) | 7 (3) |
| Other CV op-amp out → ADC (3) | 37 (9) | 37 (9) | 44 (9) | 36 (9) | 42 (9) | 42 (9) | 42 (9) |
| Codec lines U3/U4 ↔ Seed (3) | 20 (7) | 20 (7) | 20 (7) | 20 (7) | 20 (7) | 20 (7) | 20 (7) |
| Pot wipers (0.5) | 69 (48) | 86 (56) | 74 (43) | 86 (58) | 101 (51) | 84 (44) | 84 (44) |
| CV jack-level (1) | 227 (39) | 266 (44) | 280 (53) | 258 (43) | 342 (61) | 338 (66) | 338 (66) |
| Audio jack-level (1) | 253 (69) | 206 (56) | 251 (68) | 205 (55) | 137 (41) | 142 (42) | 142 (42) |
| Digital (0.5) | 143 (70) | 150 (82) | 147 (81) | 150 (82) | 137 (53) | 163 (52) | 146 (55) |
| Power (0.3) | 212 (75) | 205 (83) | 172 (74) | 169 (68) | 194 (70) | 173 (62) | 165 (59) |

| | A | B | C | D | A2 | B2 | C2 |
|---|---|---|---|---|---|---|---|
| Headers (pins) | 15/13/10 | 28/7 | 21/8/7 | 3/3/24/7 | 7/10/19 | 26/9 | 24/6/6 |
| Closest header pin to a Seed pin | 7.5 | 5.3 | 6.0 | 5.3 | 5.3 | 5.4 | 5.4 |
| microSD socket to its pins (6 lines) | 255 | 72 | 241 | 72 | 74 | 39 | 85 |
| USB socket inside the board edge | ~5 | ~5 | ~5 | ~5 | 27.5 | 26.3 | 26.3 |

## Findings

- The traces that matter (op-amp → ADC, codec) are short and nearly equal in every candidate: the floorplan always
  puts the op-amps at the Seed3's pins. The header choice moves only the tolerant traces.
- D shows that forcing a fourth header only peels supplies off into 3-pin stubs.
- **Open problem (d):** a header between the Seed3's socket rows is in a pocket. Signals that end elsewhere must
  squeeze out between the socket pins. A2-C2 put most of the CV row in that pocket, so ~10 CV traces would cross the
  right socket row where the ADC lines come in. The search doesn't model this yet. Proposed rule (not built): inside
  the pocket, a header pin carries only GND or a signal that ends at a Seed3 pin.
